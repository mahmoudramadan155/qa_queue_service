# app/celery_app.py
from celery import Celery
from app.config import settings
import os

# Create Celery instance
def make_celery():
    celery = Celery(
        "qa_service",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            "app.tasks.document_tasks",
            "app.tasks.qa_tasks",
            "app.tasks.user_tasks"
        ]
    )

    # Configure Celery
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        result_expires=3600,  # Results expire after 1 hour
        task_always_eager=settings.celery_task_always_eager,  # For testing
        
        # Task routing
        task_routes={
            "app.tasks.document_tasks.*": {"queue": "document_processing"},
            "app.tasks.qa_tasks.*": {"queue": "question_answering"},
            "app.tasks.user_tasks.*": {"queue": "user_management"},
        },
        
        # Worker configuration
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_max_tasks_per_child=1000,
        
        # Rate limiting
        task_annotations={
            "app.tasks.document_tasks.process_document_async": {"rate_limit": "10/m"},
            "app.tasks.qa_tasks.answer_question_async": {"rate_limit": "50/m"},
        },
        
        # Beat schedule for periodic tasks
        beat_schedule={
            "cleanup-expired-tasks": {
                "task": "app.tasks.user_tasks.cleanup_expired_tasks",
                "schedule": 3600.0,  # Run every hour
            },
            "update-user-stats": {
                "task": "app.tasks.user_tasks.update_user_stats",
                "schedule": 300.0,  # Run every 5 minutes
            },
        },
    )

    # celery_app.conf.broker_connection_retry_on_startup = True

    return celery

celery_app = make_celery()