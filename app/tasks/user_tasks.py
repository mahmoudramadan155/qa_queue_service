# app/tasks/user_tasks.py
from celery import current_task
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, List
from datetime import datetime, timedelta
import redis
import json

from app.celery_app import celery_app
from app.config import settings
from app.database.models import User, Document, QueryLog

# Create database session for tasks
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis connection
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

def get_task_db():
    """Get database session for tasks"""
    return SessionLocal()

@celery_app.task(
    bind=True,
    name="app.tasks.user_tasks.cleanup_expired_tasks"
)
def cleanup_expired_tasks(self) -> Dict[str, Any]:
    """
    Clean up expired tasks and temporary data
    """
    try:
        # Clean up expired Redis keys
        expired_keys = []
        
        # Get all task result keys
        for key in redis_client.scan_iter(match="celery-task-meta-*"):
            try:
                ttl = redis_client.ttl(key)
                if ttl == -1:  # No expiration set
                    redis_client.expire(key, 3600)  # Set 1 hour expiration
                elif ttl == -2:  # Key doesn't exist
                    expired_keys.append(key)
            except:
                continue
        
        # Clean up old session data
        for key in redis_client.scan_iter(match="session:*"):
            try:
                ttl = redis_client.ttl(key)
                if ttl == -2:
                    expired_keys.append(key)
            except:
                continue
        
        return {
            "status": "success",
            "cleaned_keys": len(expired_keys),
            "message": f"Cleaned up {len(expired_keys)} expired keys"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@celery_app.task(
    bind=True,
    name="app.tasks.user_tasks.update_user_stats"
)
def update_user_stats(self) -> Dict[str, Any]:
    """
    Update user statistics and metrics
    """
    db = get_task_db()
    
    try:
        updated_users = 0
        
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        
        for user in users:
            # Update document count
            doc_count = db.query(Document).filter(Document.user_id == user.id).count()
            user.document_count = doc_count
            
            # Reset daily query count if it's a new day
            if user.last_query_date and user.last_query_date.date() < datetime.utcnow().date():
                user.query_count_today = 0
            
            updated_users += 1
        
        db.commit()
        
        return {
            "status": "success",
            "updated_users": updated_users,
            "message": f"Updated stats for {updated_users} users"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(
    bind=True,
    name="app.tasks.user_tasks.generate_user_report"
)
def generate_user_report(self, user_id: int, days: int = 30) -> Dict[str, Any]:
    """
    Generate comprehensive user activity report
    """
    db = get_task_db()
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        
        # Date range
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Document statistics
        total_documents = db.query(Document).filter(Document.user_id == user_id).count()
        recent_documents = db.query(Document).filter(
            Document.user_id == user_id,
            Document.created_at >= since_date
        ).count()
        
        # Query statistics
        total_queries = db.query(QueryLog).filter(QueryLog.user_id == user_id).count()
        recent_queries = db.query(QueryLog).filter(
            QueryLog.user_id == user_id,
            QueryLog.created_at >= since_date
        ).all()
        
        # Calculate metrics
        avg_response_time = 0
        if recent_queries:
            avg_response_time = sum(q.response_time for q in recent_queries) / len(recent_queries)
        
        # Storage usage (approximate)
        total_file_size = db.query(func.sum(Document.file_size)).filter(
            Document.user_id == user_id
        ).scalar() or 0
        
        # Activity by day
        daily_activity = {}
        for query in recent_queries:
            day = query.created_at.date().isoformat()
            daily_activity[day] = daily_activity.get(day, 0) + 1
        
        report = {
            "user_id": user_id,
            "email": user.email,
            "member_since": user.created_at.isoformat(),
            "report_period_days": days,
            "documents": {
                "total": total_documents,
                "recent": recent_documents,
                "storage_mb": round(total_file_size / (1024 * 1024), 2)
            },
            "queries": {
                "total": total_queries,
                "recent": len(recent_queries),
                "avg_response_time_ms": round(avg_response_time, 2),
                "daily_activity": daily_activity
            },
            "limits": {
                "max_documents": settings.max_documents_per_user,
                "max_queries_per_hour": settings.max_queries_per_hour,
                "documents_remaining": settings.max_documents_per_user - total_documents
            }
        }
        
        # Cache report in Redis for 1 hour
        cache_key = f"user_report:{user_id}:{days}"
        redis_client.setex(cache_key, 3600, json.dumps(report))
        
        return {
            "status": "success",
            "report": report
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(
    bind=True,
    name="app.tasks.user_tasks.cleanup_inactive_users"
)
def cleanup_inactive_users(self, inactive_days: int = 90) -> Dict[str, Any]:
    """
    Clean up data for inactive users
    """
    db = get_task_db()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=inactive_days)
        
        # Find inactive users
        inactive_users = db.query(User).filter(
            User.last_query_date < cutoff_date,
            User.is_active == True
        ).all()
        
        cleaned_count = 0
        for user in inactive_users:
            current_task.update_state(
                state="PROCESSING",
                meta={
                    "status": f"Cleaning up user {user.email}",
                    "progress": (cleaned_count / len(inactive_users)) * 100
                }
            )
            
            # You could delete documents, queries, etc. here
            # For now, just mark as cleaned up in logs
            cleaned_count += 1
        
        return {
            "status": "success",
            "inactive_users_found": len(inactive_users),
            "cleaned_count": cleaned_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(
    bind=True,
    name="app.tasks.user_tasks.export_user_data"
)
def export_user_data(self, user_id: int) -> Dict[str, Any]:
    """
    Export all user data (GDPR compliance)
    """
    db = get_task_db()
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Collecting user data", "progress": 25}
        )
        
        # Collect all user data
        documents = db.query(Document).filter(Document.user_id == user_id).all()
        queries = db.query(QueryLog).filter(QueryLog.user_id == user_id).all()
        
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Formatting export data", "progress": 75}
        )
        
        export_data = {
            "user_info": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
                "is_active": user.is_active,
                "document_count": user.document_count,
                "query_count_today": user.query_count_today,
                "last_query_date": user.last_query_date.isoformat() if user.last_query_date else None
            },
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "chunk_count": doc.chunk_count,
                    "file_size": doc.file_size,
                    "created_at": doc.created_at.isoformat()
                }
                for doc in documents
            ],
            "queries": [
                {
                    "id": query.id,
                    "question": query.question,
                    "answer": query.answer,
                    "response_time": query.response_time,
                    "chunks_used": query.chunks_used,
                    "created_at": query.created_at.isoformat()
                }
                for query in queries
            ],
            "export_timestamp": datetime.utcnow().isoformat()
        }
        
        # Store export in Redis temporarily (24 hours)
        export_key = f"user_export:{user_id}:{int(datetime.utcnow().timestamp())}"
        redis_client.setex(export_key, 86400, json.dumps(export_data))
        
        return {
            "status": "success",
            "export_key": export_key,
            "data_summary": {
                "documents": len(documents),
                "queries": len(queries),
                "export_size_mb": len(json.dumps(export_data)) / (1024 * 1024)
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(
    bind=True,
    name="app.tasks.user_tasks.send_notification"
)
def send_notification(
    self, 
    user_id: int, 
    notification_type: str, 
    message: str, 
    data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Send notification to user (via Redis/WebSocket, email, etc.)
    """
    try:
        notification = {
            "user_id": user_id,
            "type": notification_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
            "read": False
        }
        
        # Store notification in Redis
        notification_key = f"notification:{user_id}:{int(datetime.utcnow().timestamp())}"
        redis_client.setex(notification_key, 604800, json.dumps(notification))  # 1 week
        
        # Add to user's notification list
        user_notifications_key = f"user_notifications:{user_id}"
        redis_client.lpush(user_notifications_key, notification_key)
        redis_client.ltrim(user_notifications_key, 0, 99)  # Keep last 100 notifications
        redis_client.expire(user_notifications_key, 604800)  # 1 week
        
        # Publish to real-time channel if needed
        redis_client.publish(f"user_channel:{user_id}", json.dumps(notification))
        
        return {
            "status": "success",
            "notification_key": notification_key,
            "message": "Notification sent successfully"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@celery_app.task(
    bind=True,
    name="app.tasks.user_tasks.process_bulk_operation"
)
def process_bulk_operation(
    self, 
    operation_type: str, 
    user_ids: List[int], 
    operation_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Process bulk operations on multiple users
    """
    try:
        results = []
        total_users = len(user_ids)
        
        for i, user_id in enumerate(user_ids):
            current_task.update_state(
                state="PROCESSING",
                meta={
                    "status": f"Processing user {i+1} of {total_users}",
                    "progress": (i / total_users) * 100,
                    "operation": operation_type
                }
            )
            
            if operation_type == "generate_report":
                result = generate_user_report.delay(user_id, operation_data.get("days", 30))
            elif operation_type == "send_notification":
                result = send_notification.delay(
                    user_id, 
                    operation_data.get("type", "info"),
                    operation_data.get("message", ""),
                    operation_data.get("data", {})
                )
            else:
                result = {"status": "error", "message": f"Unknown operation: {operation_type}"}
            
            results.append({"user_id": user_id, "result": result})
        
        return {
            "status": "success",
            "operation_type": operation_type,
            "total_users": total_users,
            "results": results
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}