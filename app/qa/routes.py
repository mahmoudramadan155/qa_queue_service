# app/qa/routes.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, AsyncGenerator, Optional
import json
import asyncio
import base64
from pathlib import Path
import redis

from app.auth.routes import get_current_user
from app.database.connection import get_db
from app.database.models import User, Document, QueryLog
from app.qa import schemas
from app.qa.services import qa_service
from app.qa.vector_store import vector_store
from app.utils.document_processor import process_document, split_text_into_chunks
from app.config import settings
from app.tasks.document_tasks import process_document_async, delete_document_async
from app.tasks.qa_tasks import answer_question_async, generate_question_suggestions
from app.tasks.user_tasks import generate_user_report

router = APIRouter(prefix="/qa", tags=["question-answering"])

# Redis client for task status tracking
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

@router.post("/upload", response_model=schemas.DocumentUpload)
async def upload_document(
    file: UploadFile = File(...),
    use_async: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process a document (with optional async processing)"""
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Supported types: {settings.allowed_extensions}"
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_file_size / (1024*1024)}MB"
        )
    
    # Check user document limit
    if current_user.document_count >= settings.max_documents_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum document limit ({settings.max_documents_per_user}) reached"
        )
    
    if use_async and not settings.celery_task_always_eager:
        # Process document asynchronously
        file_content_b64 = base64.b64encode(file_content).decode('utf-8')
        
        task = process_document_async.delay(
            user_id=current_user.id,
            filename=file.filename,
            file_content_b64=file_content_b64
        )
        
        # Store task info in Redis for status tracking
        task_info = {
            "task_id": task.id,
            "filename": file.filename,
            "status": "queued",
            "created_at": "now"
        }
        redis_client.setex(f"upload_task:{current_user.id}:{task.id}", 3600, json.dumps(task_info))
        
        return schemas.DocumentUpload(
            filename=file.filename,
            chunk_count=0,  # Will be updated when processing completes
            content_hash="",
            task_id=task.id,
            status="processing"
        )
    
    else:
        # Process document synchronously (original behavior)
        try:
            text_content, content_hash = process_document(file.filename, file_content)
            
            # Check for duplicate content
            existing_doc = db.query(Document).filter(
                Document.content_hash == content_hash,
                Document.user_id == current_user.id
            ).first()
            
            if existing_doc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Document with identical content already exists"
                )
            
            # Split text into chunks
            chunks = split_text_into_chunks(text_content)
            
            # Create document record
            document = Document(
                filename=file.filename,
                content_hash=content_hash,
                chunk_count=len(chunks),
                file_size=len(file_content),
                user_id=current_user.id
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Add chunks to vector store
            vector_store.add_chunks(chunks, document.id, current_user.id)
            
            # Update user document count
            current_user.document_count = db.query(Document).filter(Document.user_id == current_user.id).count()
            db.commit()
            
            return schemas.DocumentUpload(
                filename=file.filename,
                chunk_count=len(chunks),
                content_hash=content_hash,
                status="completed"
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing document: {str(e)}"
            )

@router.get("/upload/status/{task_id}")
async def get_upload_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of async upload task"""
    from app.celery_app import celery_app
    
    # Get task result
    task_result = celery_app.AsyncResult(task_id)
    
    # Get additional info from Redis
    task_info_key = f"upload_task:{current_user.id}:{task_id}"
    task_info = redis_client.get(task_info_key)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None,
        "info": json.loads(task_info) if task_info else None
    }
    
    if task_result.status == "PENDING":
        response["message"] = "Task is waiting to be processed"
    elif task_result.status == "PROCESSING":
        response["message"] = "Document is being processed"
        response["progress"] = task_result.info.get("progress", 0) if task_result.info else 0
    elif task_result.status == "SUCCESS":
        response["message"] = "Document processed successfully"
    elif task_result.status == "FAILURE":
        response["message"] = f"Processing failed: {str(task_result.result)}"
    
    return response

@router.post("/ask", response_model=schemas.QuestionResponse)
async def ask_question(
    question_data: schemas.QuestionRequest,
    use_async: bool = False,
    priority: str = "normal",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ask a question and get an AI-generated answer"""
    
    if not question_data.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    
    # Check rate limiting
    if settings.rate_limit_enabled:
        from datetime import datetime
        today = datetime.utcnow().date()
        if current_user.last_query_date and current_user.last_query_date.date() == today:
            if current_user.query_count_today >= settings.max_queries_per_hour:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Try again later."
                )
    
    if use_async and not settings.celery_task_always_eager:
        # Process question asynchronously
        task = answer_question_async.delay(
            user_id=current_user.id,
            question=question_data.question,
            priority=priority
        )
        
        return schemas.QuestionResponse(
            question=question_data.question,
            answer="Processing your question asynchronously...",
            response_time_ms=0,
            task_id=task.id,
            status="processing"
        )
    
    else:
        # Process question synchronously (original behavior)
        try:
            answer = qa_service.answer_question(
                question=question_data.question,
                user_id=current_user.id,
                db=db
            )
            
            # Get the last query log for response time
            last_query = db.query(QueryLog).filter(
                QueryLog.user_id == current_user.id
            ).order_by(QueryLog.id.desc()).first()
            
            response_time = last_query.response_time if last_query else 0
            
            return schemas.QuestionResponse(
                question=question_data.question,
                answer=answer,
                response_time_ms=response_time,
                status="completed"
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating answer: {str(e)}"
            )

@router.get("/ask/status/{task_id}")
async def get_question_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of async question answering task"""
    from app.celery_app import celery_app
    
    task_result = celery_app.AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }
    
    if task_result.status == "PENDING":
        response["message"] = "Question is waiting to be processed"
    elif task_result.status == "PROCESSING":
        response["message"] = "Generating answer"
        response["progress"] = task_result.info.get("progress", 0) if task_result.info else 0
    elif task_result.status == "SUCCESS":
        response["message"] = "Answer generated successfully"
    elif task_result.status == "FAILURE":
        response["message"] = f"Failed to generate answer: {str(task_result.result)}"
    
    return response

@router.post("/ask/stream")
async def ask_question_stream(
    question_data: schemas.QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ask a question and get a streaming AI-generated answer"""
    
    if not question_data.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    
    # Check rate limiting
    if settings.rate_limit_enabled:
        from datetime import datetime
        today = datetime.utcnow().date()
        if current_user.last_query_date and current_user.last_query_date.date() == today:
            if current_user.query_count_today >= settings.max_queries_per_hour:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Try again later."
                )
    
    async def generate_response() -> AsyncGenerator[str, None]:
        """Generate streaming response"""
        try:
            # Start timing
            import time
            start_time = time.time()
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Searching for relevant information...'})}\n\n"
            
            # Get relevant chunks from vector store
            similar_chunks = vector_store.search_similar_chunks(
                query=question_data.question,
                user_id=current_user.id,
                top_k=5
            )
            
            context = [chunk['content'] for chunk in similar_chunks]
            
            if not context:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No relevant documents found. Please upload documents first.'})}\n\n"
                return
            
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating answer...'})}\n\n"
            
            # Generate streaming answer
            full_answer = ""
            async for chunk in qa_service.answer_question_stream(
                question=question_data.question,
                context=context,
                user_id=current_user.id
            ):
                if chunk:
                    full_answer += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    # Small delay to make streaming visible
                    await asyncio.sleep(0.01)
            
            # Calculate response time
            response_time = int((time.time() - start_time) * 1000)
            
            # Log the complete query
            query_log = QueryLog(
                user_id=current_user.id,
                question=question_data.question,
                answer=full_answer,
                response_time=response_time,
                chunks_used=len(similar_chunks)
            )
            db.add(query_log)
            
            # Update user query count
            from datetime import datetime
            current_user.query_count_today += 1
            current_user.last_query_date = datetime.utcnow()
            
            db.commit()
            
            # Send completion status
            yield f"data: {json.dumps({'type': 'complete', 'response_time': response_time})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Error generating answer: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@router.get("/documents", response_model=List[schemas.DocumentInfo])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's uploaded documents"""
    documents = db.query(Document).filter(Document.user_id == current_user.id).all()
    return documents

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    use_async: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document and its chunks"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if use_async and not settings.celery_task_always_eager:
        # Delete document asynchronously
        task = delete_document_async.delay(document_id, current_user.id)
        
        return {
            "message": "Document deletion initiated",
            "task_id": task.id,
            "status": "processing"
        }
    
    else:
        # Delete document synchronously
        try:
            # Delete from vector store
            vector_store.delete_document_chunks(document_id, current_user.id)
            
            # Delete from database
            db.delete(document)
            
            # Update user document count
            current_user.document_count = db.query(Document).filter(Document.user_id == current_user.id).count()
            
            db.commit()
            
            return {"message": "Document deleted successfully"}
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting document: {str(e)}"
            )

@router.get("/history", response_model=List[schemas.QueryLogInfo])
async def get_query_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's query history"""
    queries = db.query(QueryLog).filter(
        QueryLog.user_id == current_user.id
    ).order_by(QueryLog.created_at.desc()).limit(limit).all()
    
    return queries

@router.get("/suggestions")
async def get_question_suggestions(
    document_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get suggested questions based on user's documents"""
    task = generate_question_suggestions.delay(current_user.id, document_id)
    
    # For immediate response, we could return cached suggestions
    # or wait a short time for the task to complete
    try:
        result = task.get(timeout=5)  # Wait up to 5 seconds
        return result
    except:
        return {
            "status": "processing",
            "task_id": task.id,
            "message": "Generating suggestions..."
        }

@router.get("/user/report")
async def get_user_report(
    days: int = 30,
    use_cache: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive user activity report"""
    
    if use_cache:
        # Check Redis cache first
        cache_key = f"user_report:{current_user.id}:{days}"
        cached_report = redis_client.get(cache_key)
        if cached_report:
            return {
                "status": "success",
                "report": json.loads(cached_report),
                "from_cache": True
            }
    
    # Generate new report
    task = generate_user_report.delay(current_user.id, days)
    
    try:
        result = task.get(timeout=10)  # Wait up to 10 seconds
        return result
    except:
        return {
            "status": "processing",
            "task_id": task.id,
            "message": "Generating report..."
        }

@router.get("/user/notifications")
async def get_user_notifications(
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """Get user notifications"""
    try:
        user_notifications_key = f"user_notifications:{current_user.id}"
        notification_keys = redis_client.lrange(user_notifications_key, 0, limit - 1)
        
        notifications = []
        for key in notification_keys:
            notification_data = redis_client.get(key)
            if notification_data:
                notifications.append(json.loads(notification_data))
        
        return {
            "status": "success",
            "notifications": notifications,
            "total": len(notifications)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "notifications": []
        }

@router.post("/user/notifications/{notification_key}/read")
async def mark_notification_read(
    notification_key: str,
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read"""
    try:
        notification_data = redis_client.get(notification_key)
        if notification_data:
            notification = json.loads(notification_data)
            if notification["user_id"] == current_user.id:
                notification["read"] = True
                redis_client.setex(notification_key, 604800, json.dumps(notification))
                return {"status": "success", "message": "Notification marked as read"}
        
        return {"status": "error", "message": "Notification not found"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/system/queues")
async def get_queue_status(
    current_user: User = Depends(get_current_user)
):
    """Get current queue status and system load"""
    from app.celery_app import celery_app
    
    try:
        # Get active tasks
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        
        # Get queue lengths from Redis
        queue_lengths = {}
        for queue_name in ["document_processing", "question_answering", "user_management"]:
            queue_key = f"celery"  # Simplified - actual implementation would check specific queues
            queue_lengths[queue_name] = redis_client.llen(queue_key) if redis_client.exists(queue_key) else 0
        
        return {
            "status": "success",
            "queue_lengths": queue_lengths,
            "active_tasks": len(active_tasks) if active_tasks else 0,
            "scheduled_tasks": len(scheduled_tasks) if scheduled_tasks else 0,
            "system_load": "normal"  # Could implement actual load checking
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "queue_lengths": {},
            "active_tasks": 0
        }

@router.post("/system/priority-question")
async def ask_priority_question(
    question_data: schemas.QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ask a high-priority question (for premium users or urgent cases)"""
    
    if not question_data.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    
    # Process with high priority
    task = answer_question_async.apply_async(
        args=[current_user.id, question_data.question],
        kwargs={"priority": "high"},
        queue=settings.high_priority_queue
    )
    
    return {
        "message": "High-priority question submitted",
        "task_id": task.id,
        "status": "processing",
        "priority": "high"
    }

@router.get("/llm-status")
async def get_llm_status(
    current_user: User = Depends(get_current_user)
):
    """Get information about the current LLM being used"""
    try:
        llm_info = qa_service.get_llm_info()
        
        # Add queue information
        queue_status = {
            "document_processing_queue": "active",
            "qa_queue": "active",
            "worker_status": "healthy"
        }
        
        return {
            "status": "success",
            "llm_info": llm_info,
            "queue_status": queue_status,
            "settings": {
                "ollama_enabled": settings.ollama_enabled,
                "ollama_url": settings.ollama_url,
                "ollama_model": settings.ollama_model,
                "has_openai_key": bool(settings.openai_api_key),
                "celery_enabled": not settings.celery_task_always_eager,
                "redis_connected": redis_client.ping() if redis_client else False
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "llm_info": {"type": "Unknown"},
            "queue_status": {"status": "error"}
        }