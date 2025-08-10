# app/tasks/qa_tasks.py
from celery import current_task
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Optional, Dict, Any, List, AsyncGenerator
import time
import asyncio
from datetime import datetime, timedelta

from app.celery_app import celery_app
from app.config import settings
from app.database.models import QueryLog, User
from app.qa.vector_store import vector_store
from app.qa.services import qa_service

# Create database session for tasks
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_task_db():
    """Get database session for tasks"""
    return SessionLocal()

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
    time_limit=settings.qa_task_timeout,
    name="app.tasks.qa_tasks.answer_question_async"
)
def answer_question_async(
    self,
    user_id: int,
    question: str,
    context: Optional[List[str]] = None,
    priority: str = "normal"
) -> Dict[str, Any]:
    """
    Answer question asynchronously
    """
    db = get_task_db()
    
    try:
        start_time = time.time()
        
        # Update task status
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Searching for relevant information", "progress": 0}
        )
        
        # Check user exists and rate limits
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Check rate limiting
        if settings.rate_limit_enabled:
            today = datetime.utcnow().date()
            if user.last_query_date and user.last_query_date.date() == today:
                if user.query_count_today >= settings.max_queries_per_hour:
                    raise ValueError("Rate limit exceeded. Try again later.")
            else:
                user.query_count_today = 0
                user.last_query_date = datetime.utcnow()
        
        # Get relevant chunks if not provided
        if not context:
            current_task.update_state(
                state="PROCESSING",
                meta={"status": "Retrieving relevant chunks", "progress": 25}
            )
            
            similar_chunks = vector_store.search_similar_chunks(
                query=question,
                user_id=user_id,
                top_k=5
            )
            context = [chunk['content'] for chunk in similar_chunks]
            chunks_used = len(similar_chunks)
        else:
            chunks_used = len(context)
        
        if not context:
            return {
                "status": "no_context",
                "message": "No relevant documents found. Please upload documents first.",
                "answer": "I don't have any relevant information to answer your question. Please upload some documents first."
            }
        
        # Generate answer
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Generating answer", "progress": 50}
        )
        
        answer = qa_service.llm.generate_answer(question, context)
        
        # Calculate response time
        response_time = int((time.time() - start_time) * 1000)
        
        current_task.update_state(
            state="PROCESSING",
            meta={"status": "Saving query log", "progress": 90}
        )
        
        # Log the query
        query_log = QueryLog(
            user_id=user_id,
            question=question,
            answer=answer,
            response_time=response_time,
            chunks_used=chunks_used
        )
        db.add(query_log)
        
        # Update user query count
        user.query_count_today += 1
        user.last_query_date = datetime.utcnow()
        
        db.commit()
        
        current_task.update_state(
            state="SUCCESS",
            meta={"status": "Answer generated successfully", "progress": 100}
        )
        
        return {
            "status": "success",
            "question": question,
            "answer": answer,
            "response_time_ms": response_time,
            "chunks_used": chunks_used,
            "query_id": query_log.id
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
    time_limit=settings.qa_task_timeout * 2,  # Longer timeout for batch processing
    name="app.tasks.qa_tasks.batch_answer_questions"
)
def batch_answer_questions(
    self, 
    user_id: int, 
    questions: List[str]
) -> Dict[str, Any]:
    """
    Answer multiple questions in batch
    """
    db = get_task_db()
    
    try:
        results = []
        total_questions = len(questions)
        
        for i, question in enumerate(questions):
            current_task.update_state(
                state="PROCESSING",
                meta={
                    "status": f"Processing question {i+1} of {total_questions}",
                    "progress": (i / total_questions) * 100,
                    "current_question": question[:50] + "..." if len(question) > 50 else question
                }
            )
            
            # Process each question
            result = answer_question_async.apply_async(
                args=[user_id, question],
                countdown=i * 2  # Stagger requests
            ).get()
            
            results.append(result)
            
            # Small delay to prevent overwhelming the system
            time.sleep(1)
        
        return {
            "status": "success",
            "total_questions": total_questions,
            "results": results,
            "message": f"Processed {total_questions} questions successfully"
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(
    bind=True,
    name="app.tasks.qa_tasks.generate_question_suggestions"
)
def generate_question_suggestions(self, user_id: int, document_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate suggested questions based on user's documents
    """
    db = get_task_db()
    
    try:
        # Get sample chunks from user's documents
        if document_id:
            # Get chunks from specific document
            similar_chunks = vector_store.search_similar_chunks(
                query="main topics summary overview",
                user_id=user_id,
                top_k=3
            )
        else:
            # Get diverse chunks from all user documents
            similar_chunks = vector_store.search_similar_chunks(
                query="key information important facts",
                user_id=user_id,
                top_k=5
            )
        
        if not similar_chunks:
            return {
                "status": "no_documents",
                "suggestions": [],
                "message": "No documents found to generate suggestions"
            }
        
        # Simple question generation based on content
        suggestions = []
        content_samples = [chunk['content'][:200] for chunk in similar_chunks]
        
        # Generate basic question templates
        question_templates = [
            "What is the main topic discussed in the documents?",
            "Can you summarize the key points?",
            "What are the important facts mentioned?",
            "How does this relate to [specific topic]?",
            "What conclusions can be drawn?"
        ]
        
        # You could use an LLM here to generate more sophisticated questions
        suggestions = question_templates[:3]  # Return top 3 suggestions
        
        return {
            "status": "success",
            "suggestions": suggestions,
            "based_on_chunks": len(similar_chunks)
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(
    bind=True,
    name="app.tasks.qa_tasks.analyze_query_patterns"
)
def analyze_query_patterns(self, user_id: int, days: int = 7) -> Dict[str, Any]:
    """
    Analyze user's query patterns and provide insights
    """
    db = get_task_db()
    
    try:
        # Get recent queries
        since_date = datetime.utcnow() - timedelta(days=days)
        recent_queries = db.query(QueryLog).filter(
            QueryLog.user_id == user_id,
            QueryLog.created_at >= since_date
        ).all()
        
        if not recent_queries:
            return {
                "status": "no_data",
                "message": f"No queries found in the last {days} days"
            }
        
        # Analyze patterns
        total_queries = len(recent_queries)
        avg_response_time = sum(q.response_time for q in recent_queries) / total_queries
        
        # Common question types (simple keyword analysis)
        question_types = {
            "what": sum(1 for q in recent_queries if "what" in q.question.lower()),
            "how": sum(1 for q in recent_queries if "how" in q.question.lower()),
            "when": sum(1 for q in recent_queries if "when" in q.question.lower()),
            "where": sum(1 for q in recent_queries if "where" in q.question.lower()),
            "why": sum(1 for q in recent_queries if "why" in q.question.lower()),
        }
        
        # Peak usage hours
        hour_counts = {}
        for query in recent_queries:
            hour = query.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None
        
        return {
            "status": "success",
            "analysis": {
                "total_queries": total_queries,
                "avg_response_time_ms": int(avg_response_time),
                "question_types": question_types,
                "peak_hour": peak_hour,
                "queries_per_day": total_queries / days
            },
            "period_days": days
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()