# app/utils/task_monitor.py
import redis
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.config import settings
from app.celery_app import celery_app

class TaskMonitor:
    """Monitor and manage Celery tasks"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        self.celery_app = celery_app
    
    def get_task_info(self, task_id: str) -> Dict[str, Any]:
        """Get comprehensive task information"""
        task_result = self.celery_app.AsyncResult(task_id)
        
        # Get additional metadata from Redis
        task_meta_key = f"task_meta:{task_id}"
        meta_data = self.redis_client.get(task_meta_key)
        
        return {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None,
            "traceback": task_result.traceback if task_result.failed() else None,
            "metadata": json.loads(meta_data) if meta_data else {},
            "created_at": task_result.date_done,
            "worker": getattr(task_result, 'worker', None)
        }
    
    def get_user_tasks(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all tasks for a specific user"""
        # Get task IDs associated with user
        user_tasks_key = f"user_tasks:{user_id}"
        task_ids = self.redis_client.lrange(user_tasks_key, 0, limit - 1)
        
        tasks = []
        for task_id in task_ids:
            task_info = self.get_task_info(task_id)
            tasks.append(task_info)
        
        return tasks
    
    def track_user_task(self, user_id: int, task_id: str, task_type: str, metadata: Dict[str, Any] = None):
        """Track a task for a user"""
        # Add to user's task list
        user_tasks_key = f"user_tasks:{user_id}"
        self.redis_client.lpush(user_tasks_key, task_id)
        self.redis_client.ltrim(user_tasks_key, 0, 99)  # Keep last 100 tasks
        self.redis_client.expire(user_tasks_key, 86400 * 7)  # 1 week
        
        # Store task metadata
        task_meta = {
            "user_id": user_id,
            "task_type": task_type,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        task_meta_key = f"task_meta:{task_id}"
        self.redis_client.setex(task_meta_key, 86400, json.dumps(task_meta))  # 24 hours
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics for all queues"""
        inspect = self.celery_app.control.inspect()
        
        try:
            # Get active tasks
            active = inspect.active() or {}
            scheduled = inspect.scheduled() or {}
            reserved = inspect.reserved() or {}
            
            # Count tasks by queue
            queue_stats = {}
            
            for worker, tasks in active.items():
                for task in tasks:
                    queue = task.get('delivery_info', {}).get('routing_key', 'default')
                    if queue not in queue_stats:
                        queue_stats[queue] = {"active": 0, "scheduled": 0, "reserved": 0}
                    queue_stats[queue]["active"] += 1
            
            for worker, tasks in scheduled.items():
                for task in tasks:
                    queue = task.get('delivery_info', {}).get('routing_key', 'default')
                    if queue not in queue_stats:
                        queue_stats[queue] = {"active": 0, "scheduled": 0, "reserved": 0}
                    queue_stats[queue]["scheduled"] += 1
            
            for worker, tasks in reserved.items():
                for task in tasks:
                    queue = task.get('delivery_info', {}).get('routing_key', 'default')
                    if queue not in queue_stats:
                        queue_stats[queue] = {"active": 0, "scheduled": 0, "reserved": 0}
                    queue_stats[queue]["reserved"] += 1
            
            return {
                "queues": queue_stats,
                "total_active": sum(len(tasks) for tasks in active.values()),
                "total_scheduled": sum(len(tasks) for tasks in scheduled.values()),
                "total_reserved": sum(len(tasks) for tasks in reserved.values()),
                "workers": list(active.keys())
            }
            
        except Exception as e:
            return {"error": str(e), "queues": {}}
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        inspect = self.celery_app.control.inspect()
        
        try:
            stats = inspect.stats() or {}
            active = inspect.active() or {}
            
            worker_info = {}
            for worker, worker_stats in stats.items():
                worker_info[worker] = {
                    "status": "online",
                    "load": worker_stats.get("rusage", {}).get("utime", 0),
                    "memory": worker_stats.get("rusage", {}).get("maxrss", 0),
                    "active_tasks": len(active.get(worker, [])),
                    "total_tasks": worker_stats.get("total", {}),
                    "pool": worker_stats.get("pool", {})
                }
            
            return {"workers": worker_info, "total_workers": len(worker_info)}
            
        except Exception as e:
            return {"error": str(e), "workers": {}}
    
    def cancel_task(self, task_id: str, user_id: Optional[int] = None) -> bool:
        """Cancel a running task"""
        try:
            # Verify user ownership if user_id provided
            if user_id:
                task_meta_key = f"task_meta:{task_id}"
                meta_data = self.redis_client.get(task_meta_key)
                if meta_data:
                    meta = json.loads(meta_data)
                    if meta.get("user_id") != user_id:
                        return False
            
            # Cancel the task
            self.celery_app.control.revoke(task_id, terminate=True)
            return True
            
        except Exception:
            return False
    
    def retry_task(self, task_id: str, user_id: Optional[int] = None) -> Optional[str]:
        """Retry a failed task"""
        try:
            # Get original task info
            task_meta_key = f"task_meta:{task_id}"
            meta_data = self.redis_client.get(task_meta_key)
            
            if not meta_data:
                return None
            
            meta = json.loads(meta_data)
            
            # Verify user ownership if user_id provided
            if user_id and meta.get("user_id") != user_id:
                return None
            
            # Get task result to check if it failed
            task_result = self.celery_app.AsyncResult(task_id)
            if task_result.status != "FAILURE":
                return None
            
            # Create new task based on original task type
            task_type = meta.get("task_type")
            original_metadata = meta.get("metadata", {})
            
            if task_type == "document_processing":
                from app.tasks.document_tasks import process_document_async
                new_task = process_document_async.delay(
                    user_id=meta["user_id"],
                    filename=original_metadata.get("filename"),
                    file_content_b64=original_metadata.get("file_content_b64")
                )
                
            elif task_type == "question_answering":
                from app.tasks.qa_tasks import answer_question_async
                new_task = answer_question_async.delay(
                    user_id=meta["user_id"],
                    question=original_metadata.get("question"),
                    priority=original_metadata.get("priority", "normal")
                )
            else:
                return None
            
            # Track the new task
            self.track_user_task(
                user_id=meta["user_id"],
                task_id=new_task.id,
                task_type=task_type,
                metadata=original_metadata
            )
            
            return new_task.id
            
        except Exception:
            return None
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Clean up old task metadata"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cleaned_count = 0
        
        # Get all task metadata keys
        for key in self.redis_client.scan_iter(match="task_meta:*"):
            try:
                meta_data = self.redis_client.get(key)
                if meta_data:
                    meta = json.loads(meta_data)
                    created_at = datetime.fromisoformat(meta.get("created_at", ""))
                    
                    if created_at < cutoff_date:
                        self.redis_client.delete(key)
                        cleaned_count += 1
            except:
                # Delete invalid metadata
                self.redis_client.delete(key)
                cleaned_count += 1
        
        return cleaned_count
    
    def get_task_analytics(self, user_id: Optional[int] = None, days: int = 7) -> Dict[str, Any]:
        """Get task analytics"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all task metadata
        analytics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "pending_tasks": 0,
            "task_types": {},
            "avg_completion_time": 0,
            "success_rate": 0
        }
        
        pattern = f"task_meta:*" if not user_id else f"user_tasks:{user_id}"
        
        completion_times = []
        
        for key in self.redis_client.scan_iter(match="task_meta:*"):
            try:
                meta_data = self.redis_client.get(key)
                if not meta_data:
                    continue
                
                meta = json.loads(meta_data)
                created_at = datetime.fromisoformat(meta.get("created_at", ""))
                
                if created_at < since_date:
                    continue
                
                # Filter by user if specified
                if user_id and meta.get("user_id") != user_id:
                    continue
                
                task_id = key.split(":")[-1]
                task_result = self.celery_app.AsyncResult(task_id)
                
                analytics["total_tasks"] += 1
                
                # Count by type
                task_type = meta.get("task_type", "unknown")
                analytics["task_types"][task_type] = analytics["task_types"].get(task_type, 0) + 1
                
                # Count by status
                if task_result.status == "SUCCESS":
                    analytics["completed_tasks"] += 1
                    # Calculate completion time if available
                    if task_result.date_done:
                        completion_time = (task_result.date_done - created_at).total_seconds()
                        completion_times.append(completion_time)
                elif task_result.status == "FAILURE":
                    analytics["failed_tasks"] += 1
                else:
                    analytics["pending_tasks"] += 1
                    
            except Exception:
                continue
        
        # Calculate averages
        if completion_times:
            analytics["avg_completion_time"] = sum(completion_times) / len(completion_times)
        
        if analytics["total_tasks"] > 0:
            analytics["success_rate"] = analytics["completed_tasks"] / analytics["total_tasks"]
        
        return analytics

# Global task monitor instance
task_monitor = TaskMonitor()