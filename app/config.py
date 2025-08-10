# app/config.py
import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./qa_service.db"
    
    # Authentication
    secret_key: str = "your-super-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # OpenAI
    openai_api_key: Optional[str] = None

    # Ollama Configuration
    ollama_enabled: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:1.7b"
    ollama_timeout: int = 60  # seconds
    
    # Vector Database Configuration
    vector_db_type: Literal["chromadb", "elasticsearch", "qdrant"] = "chromadb"
    
    # ChromaDB Configuration
    chroma_persist_directory: str = "./chroma_db"

    # Elasticsearch Configuration
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "qa_documents"

    # Qdrant Configuration
    qdrant_url: Optional[str] = None  # Use None for local mode, or "http://localhost:6333" for server mode
    qdrant_api_key: Optional[str] = None  # Optional API key for Qdrant Cloud
    qdrant_persist_directory: str = "./qdrant_db"  # For local mode only
    qdrant_collection_name: str = "qa_documents"
    qdrant_timeout: int = 60  # seconds

    # Embedding Model (shared across all vector stores)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2" 
    
    # File Upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: list = [".txt", ".pdf"]
    
    # Multi-user Configuration
    max_documents_per_user: int = 100
    max_chunks_per_document: int = 1000
    max_queries_per_hour: int = 100
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False  # Set to True for testing without Celery worker
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 1  # Different DB for caching
    redis_password: Optional[str] = None
    redis_max_connections: int = 50
    
    # RabbitMQ Configuration (alternative to Redis broker)
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672//"
    use_rabbitmq: bool = False  # Set to True to use RabbitMQ instead of Redis as broker
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 100
    
    # Task Timeouts (in seconds)
    document_processing_timeout: int = 600  # 10 minutes
    qa_task_timeout: int = 180  # 3 minutes
    user_task_timeout: int = 60  # 1 minute
    
    # Queue Priorities
    high_priority_queue: str = "high_priority"
    normal_priority_queue: str = "normal"
    low_priority_queue: str = "low_priority"
    
    # Logging
    log_level: str = "INFO"
    
    # Docker/Production
    postgres_db: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None

    @property
    def celery_broker_url_computed(self) -> str:
        """Get the appropriate broker URL based on configuration"""
        if self.use_rabbitmq:
            return self.rabbitmq_url
        return self.celery_broker_url

settings = Settings()