# AI Question-Answering Service - Complete Project Breakdown

## 📋 Project Overview

This is a **production-ready AI-powered Question-Answering service** that allows users to upload documents and ask questions about their content using Retrieval-Augmented Generation (RAG). The system processes documents, stores them in vector databases, and uses AI models to provide contextual answers.

## 🏗️ System Architecture

### Core Technologies
- **FastAPI**: Web framework for building the REST API
- **SQLAlchemy**: Database ORM for PostgreSQL/SQLite
- **Celery**: Distributed task queue for background processing
- **Redis**: Message broker and caching layer
- **Vector Databases**: Multiple options (Qdrant, ChromaDB, Elasticsearch)
- **Docker**: Containerization for deployment
- **AI Models**: Ollama (local) or OpenAI GPT integration

### Architecture Pattern
The system follows a **microservices-like architecture** with:
- **API Layer**: FastAPI application handling HTTP requests
- **Task Workers**: Celery workers for async processing
- **Storage Layer**: PostgreSQL for metadata, Vector DB for embeddings
- **AI Layer**: Local or cloud-based language models

## 📁 Project Structure Breakdown

### 1. Authentication System (`app/auth/`)

**Files**: `routes.py`, `schemas.py`, `utils.py`

**Purpose**: Handles user registration, login, and JWT-based authentication.

**Key Features**:
- User registration with email validation
- JWT token-based authentication
- Password hashing with bcrypt
- Protected route middleware

**Flow**:
1. User registers → Password hashed → User stored in database
2. User logs in → Credentials verified → JWT token issued
3. Protected endpoints validate JWT tokens

### 2. Database Layer (`app/database/`)

**Files**: `connection.py`, `models.py`

**Models**:
- **User**: Stores user info, document counts, query limits
- **Document**: File metadata, content hash, chunk count
- **QueryLog**: Question/answer history with response times
- **UserSession**: Session tracking for analytics

**Features**:
- Multi-user isolation
- Document deduplication via content hashing
- Query rate limiting per user
- Performance indexes for fast queries

### 3. Question-Answering Core (`app/qa/`)

#### Vector Store System (`vector_store.py`)
**Purpose**: Manages document embeddings and similarity search

**Supported Vector Databases**:
- **Qdrant**: High-performance vector search (recommended)
- **ChromaDB**: Simple local vector storage
- **Elasticsearch**: Enterprise search with vector capabilities

**Key Operations**:
- Convert text chunks to vector embeddings
- Store embeddings with user isolation
- Perform similarity search for questions
- Delete user/document data

#### AI Services (`services.py`)
**Multiple LLM Options**:
- **SimpleLLM**: Basic fallback using context matching
- **OllamaLLM**: Local models (Qwen, Llama, etc.)
- **OpenAILLM**: GPT-3.5/GPT-4 via API

**Features**:
- Automatic LLM selection based on availability
- Streaming response support
- Context-aware answer generation
- Fallback mechanisms

#### API Routes (`routes.py`)
**Endpoints**:
- `POST /qa/upload`: Document upload (sync/async)
- `POST /qa/ask`: Ask questions (sync/async/streaming)
- `GET /qa/documents`: List user documents
- `DELETE /qa/documents/{id}`: Remove documents
- `GET /qa/history`: Query history
- `GET /qa/suggestions`: AI-generated question suggestions

### 4. Background Task System (`app/tasks/`)

#### Document Processing (`document_tasks.py`)
**Tasks**:
- `process_document_async`: Extract text, create chunks, store embeddings
- `delete_document_async`: Remove document and associated data
- `bulk_delete_user_documents`: Clean up user data

**Process Flow**:
1. Receive uploaded file
2. Extract text (PDF/TXT support)
3. Split into overlapping chunks
4. Generate embeddings
5. Store in vector database
6. Update user statistics

#### QA Tasks (`qa_tasks.py`)
**Tasks**:
- `answer_question_async`: Generate answers with context retrieval
- `batch_answer_questions`: Process multiple questions
- `generate_question_suggestions`: AI-suggested questions
- `analyze_query_patterns`: User behavior analytics

#### User Management (`user_tasks.py`)
**Tasks**:
- `cleanup_expired_tasks`: Remove old task data
- `update_user_stats`: Refresh user metrics
- `generate_user_report`: Comprehensive activity reports
- `export_user_data`: GDPR compliance data export

### 5. Utilities (`app/utils/`)

#### Document Processing (`document_processor.py`)
- **PDF Text Extraction**: Using PyPDF2
- **Text Chunking**: Smart splitting with overlap
- **Content Hashing**: SHA-256 for deduplication

#### Task Monitoring (`task_monitor.py`)
- **Task Tracking**: Monitor Celery task status
- **Queue Statistics**: Real-time queue metrics
- **Worker Health**: Monitor worker performance
- **Task Analytics**: Success rates, completion times

## 🔄 Complete User Flow

### 1. User Registration & Authentication
```
User Registration → Password Hashing → Database Storage → JWT Token
```

### 2. Document Upload Process
```
File Upload → Validation → Text Extraction → Chunking → 
Embedding Generation → Vector Storage → Metadata Update
```

### 3. Question-Answering Process
```
Question Input → Vector Search → Context Retrieval → 
LLM Processing → Answer Generation → Response Logging
```

## 🚀 Deployment Architecture

### Development Setup
- **Local Database**: SQLite for simplicity
- **Local Vector DB**: Qdrant or ChromaDB
- **Local LLM**: Ollama with lightweight models
- **Task Queue**: Redis + Celery workers

### Production Setup (Docker Compose)
**Services**:
- **Web App**: FastAPI application (port 8009)
- **PostgreSQL**: Primary database (port 5432)
- **Redis**: Message broker (port 6379)
- **Qdrant**: Vector database (port 6333)
- **Ollama**: Local LLM server (port 11434)
- **Celery Workers**: 3 specialized workers
- **Flower**: Task monitoring UI (port 5555)
- **Nginx**: Load balancer (optional)

### Worker Specialization
- **Document Worker**: Handles file processing (CPU-intensive)
- **QA Worker**: Manages question answering (GPU/LLM-intensive)
- **User Worker**: Background maintenance tasks

## 🔧 Configuration Management

### Environment Variables (`.env`)
**Database Settings**:
- `DATABASE_URL`: PostgreSQL or SQLite connection
- `VECTOR_DB_TYPE`: Choose vector database (qdrant/chromadb/elasticsearch)

**AI Configuration**:
- `OLLAMA_ENABLED`: Use local Ollama models
- `OLLAMA_MODEL`: Specific model (qwen3:1.7b, llama2, etc.)
- `OPENAI_API_KEY`: Optional OpenAI integration

**Scaling Settings**:
- `MAX_DOCUMENTS_PER_USER`: User upload limits
- `MAX_QUERIES_PER_HOUR`: Rate limiting
- `CELERY_TASK_ALWAYS_EAGER`: Sync mode for testing

## 📊 Advanced Features

### Real-time Capabilities
- **Streaming Responses**: Real-time answer generation
- **WebSocket Support**: Live task updates
- **Progress Tracking**: Upload/processing status

### Analytics & Monitoring
- **User Reports**: Activity dashboards
- **Query Analytics**: Response time tracking
- **System Health**: Worker and queue monitoring
- **Performance Metrics**: Success rates, resource usage

### Multi-tenancy
- **User Isolation**: Vector search scoped to user
- **Resource Limits**: Per-user quotas
- **Data Privacy**: Secure data separation

### Extensibility
- **Plugin Architecture**: Easy LLM integration
- **Multiple Vector DBs**: Vendor flexibility
- **Custom Embeddings**: Configurable models
- **API Versioning**: Backward compatibility

## 🛠️ Getting Started

### Quick Local Setup
```bash
# 1. Clone and setup
git clone <repo>
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Start services
redis-server  # In one terminal
python -m uvicorn app.main:app --reload  # In another

# 4. Start Celery workers (optional)
./scripts/start_celery.sh
```

### Docker Deployment
```bash
# Full production stack
docker-compose up --build

# Access services
# API: http://localhost:8009
# Flower: http://localhost:5555
# Docs: http://localhost:8009/docs
```

## 🎯 Use Cases

**Enterprise Document Q&A**: Upload company docs, ask policy questions
**Research Assistant**: Academic papers analysis and synthesis
**Customer Support**: Knowledge base for support agents
**Legal Document Review**: Contract and regulation queries
**Educational Platform**: Course material question answering

## 🔒 Security Features

- **JWT Authentication**: Secure API access
- **User Isolation**: Data privacy guarantees
- **Rate Limiting**: Abuse prevention
- **Input Validation**: XSS and injection protection
- **HTTPS Support**: Encrypted communication (production)

This project represents a **complete, production-ready RAG system** with enterprise-level features like multi-tenancy, background processing, monitoring, and scalable deployment options.