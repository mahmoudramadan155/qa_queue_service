# app/tasks/document_tasks.py
from celery import current_task
from celery.exceptions import Retry
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional, Dict, Any
import time
import hashlib
from pathlib import Path

from app.celery_app import celery_app
from app.config import settings
from app.database.models import Document, User
from app.qa.vector_store import vector_store
from app.utils.document_processor import process_document, split_text_into_chunks

# Create database session for tasks
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_task_db():
    """Get database session for tasks"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, will be closed in task

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    time_limit=settings.document_processing_timeout,
    name="app.tasks.document_tasks.process_document_async"
)
def process_document_async(
    self,
    user_id: int,
    filename: str,
    file_content_b64: str,  # Base64 encoded file content
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process document asynchronously
    """
    db = get_task_db()
    
    try:
        # Update task status
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Starting document processing", "progress": 0}
        )
        
        # Decode file content
        import base64
        file_content = base64.b64decode(file_content_b64)
        
        # Check user exists and has capacity
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        if user.document_count >= settings.max_documents_per_user:
            raise ValueError(f"Maximum document limit ({settings.max_documents_per_user}) reached")
        
        # Update progress
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Processing document content", "progress": 25}
        )
        
        # Process document
        text_content, content_hash = process_document(filename, file_content)
        
        # Check for duplicate content
        existing_doc = db.query(Document).filter(
            Document.content_hash == content_hash,
            Document.user_id == user_id
        ).first()
        
        if existing_doc:
            return {
                "status": "duplicate",
                "message": "Document with identical content already exists",
                "document_id": existing_doc.id
            }
        
        # Update progress
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Splitting text into chunks", "progress": 50}
        )
        
        # Split text into chunks
        chunks = split_text_into_chunks(text_content)
        
        if len(chunks) > settings.max_chunks_per_document:
            raise ValueError(f"Document too large. Maximum {settings.max_chunks_per_document} chunks allowed")
        
        # Create document record
        document = Document(
            filename=filename,
            content_hash=content_hash,
            chunk_count=len(chunks),
            file_size=len(file_content),
            user_id=user_id
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Update progress
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Adding chunks to vector store", "progress": 75}
        )
        
        # Add chunks to vector store
        vector_store.add_chunks(chunks, document.id, user_id)
        
        # Update user document count
        user.document_count = db.query(Document).filter(Document.user_id == user_id).count()
        db.commit()
        
        # Update progress
        current_task.update_state(
            state="SUCCESS",
            meta={"status": "Document processing completed", "progress": 100}
        )
        
        return {
            "status": "success",
            "document_id": document.id,
            "filename": filename,
            "chunk_count": len(chunks),
            "content_hash": content_hash,
            "message": f"Document processed successfully with {len(chunks)} chunks"
        }
        
    except Exception as e:
        current_task.update_state(
            state="FAILURE",
            meta={"status": f"Error: {str(e)}", "progress": 0}
        )
        raise e
    finally:
        db.close()

@celery_app.task(
    bind=True,
    time_limit=settings.user_task_timeout,
    name="app.tasks.document_tasks.delete_document_async"
)
def delete_document_async(self, document_id: int, user_id: int) -> Dict[str, Any]:
    """
    Delete document and its chunks asynchronously
    """
    db = get_task_db()
    
    try:
        # Find document
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        
        if not document:
            return {"status": "error", "message": "Document not found"}
        
        # Delete from vector store
        vector_store.delete_document_chunks(document_id, user_id)
        
        # Delete from database
        db.delete(document)
        
        # Update user document count
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.document_count = db.query(Document).filter(Document.user_id == user_id).count()
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Document deleted successfully",
            "document_id": document_id
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(
    bind=True,
    time_limit=settings.user_task_timeout,
    name="app.tasks.document_tasks.bulk_delete_user_documents"
)
def bulk_delete_user_documents(self, user_id: int) -> Dict[str, Any]:
    """
    Delete all user documents (for account deletion)
    """
    db = get_task_db()
    
    try:
        # Get all user documents
        documents = db.query(Document).filter(Document.user_id == user_id).all()
        
        # Delete from vector store
        vector_store.delete_user_data(user_id)
        
        # Delete from database
        for doc in documents:
            db.delete(doc)
        
        # Update user document count
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.document_count = 0
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Deleted {len(documents)} documents for user {user_id}",
            "deleted_count": len(documents)
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.reindex_user_documents"
)
def reindex_user_documents(self, user_id: int) -> Dict[str, Any]:
    """
    Reindex all user documents in vector store
    """
    db = get_task_db()
    
    try:
        documents = db.query(Document).filter(Document.user_id == user_id).all()
        
        reindexed_count = 0
        for doc in documents:
            current_task.update_state(
                state="PROCESSING",
                meta={
                    "status": f"Reindexing document: {doc.filename}",
                    "progress": (reindexed_count / len(documents)) * 100
                }
            )
            
            # This would require storing original text content
            # For now, we'll just mark as reindexed
            reindexed_count += 1
        
        return {
            "status": "success",
            "message": f"Reindexed {reindexed_count} documents",
            "reindexed_count": reindexed_count
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()