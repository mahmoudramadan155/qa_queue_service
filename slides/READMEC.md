# QA Service with Celery Integration

This document explains how to set up and use the enhanced QA service with Celery, Redis, and RabbitMQ for handling multi-user queuing and background task processing.

## Architecture Overview

The system now includes:
- **FastAPI Web Application**: Main API server
- **Celery Workers**: Background task processors
- **Redis**: Message broker and cache
- **RabbitMQ**: Alternative message broker (optional)
- **PostgreSQL**: Main database
- **Qdrant**: Vector database
- **Flower**: Celery monitoring dashboard

## Task Queues

### Queue Types
1. **document_processing**: Document upload and processing
2. **question_answering**: AI question answering tasks
3. **high_priority**: Urgent questions (premium users)
4. **user_management**: User analytics and maintenance

### Task Types
- **Document Processing**: Async file upload, text extraction, chunking, vector storage
- **Question Answering**: AI-powered responses with context retrieval
- **User Analytics**: Report generation, usage statistics
- **System Maintenance**: Cleanup, monitoring, notifications

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Redis

```bash
# Install Redis
sudo apt-get install redis-server

# Start Redis
redis-server

# Verify Redis is running
redis-cli ping
```

### 3. Set Up RabbitMQ (Optional)

```bash
# Install RabbitMQ
sudo apt-get install rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Access management UI: http://localhost:15672
# Default credentials: guest/guest
```

### 4. Configure Environment

Update your `.env` file with Celery settings:

```env
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=false

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_DB=1

# Alternative: RabbitMQ Configuration
RABBITMQ_URL=amqp://guest:guest@localhost:5672//
USE_RABBITMQ=false
```

### 5. Start Services

#### Option A: Using Scripts

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Start all Celery services
./scripts/start_celery.sh

# Check status
./scripts/celery_status.sh

# Stop all services
./scripts/stop_celery.sh
```

#### Option B: Manual Start

```bash
# Start workers in separate terminals

# Document processing worker
celery -A app.celery_app:celery_app worker --loglevel=info --queues=document_processing --concurrency=2 --hostname=worker-docs@%h

# Question answering worker
celery -A app.celery_app:celery_app worker --loglevel=info --queues=question_answering,high_priority --concurrency=4 --hostname=worker-qa@%h

# User management worker
celery -A app.celery_app:celery_app worker --loglevel=info --queues=user_management --concurrency=2 --hostname=worker-users@%h

# Beat scheduler
celery -A app.celery_app:celery_app beat --loglevel=info

# Flower monitoring
celery -A app.celery_app:celery_app flower --port=5555
```

#### Option C: Docker Compose

```bash
# Start all services with Docker
docker-compose up -d

# Check logs
docker-compose logs -f celery-worker-qa

# Scale workers
docker-compose up -d --scale celery-worker-qa=3
```

## API Usage

### Async Document Upload

```python
# Upload document asynchronously
response = requests.post("/qa/upload?use_async=true", 
                        files={"file": open("document.pdf", "rb")},
                        headers={"Authorization": "Bearer YOUR_TOKEN"})

task_id = response.json()["task_id"]

# Check upload status
status = requests.get(f"/qa/upload/status/{task_id}",
                     headers={"Authorization": "Bearer YOUR_TOKEN"})
```

### Async Question Answering

```python
# Ask question asynchronously
response = requests.post("/qa/ask?use_async=true",
                        json={"question": "What is this document about?"},
                        headers={"Authorization": "Bearer YOUR_TOKEN"})

task_id = response.json()["task_id"]

# Check answer status
status = requests.get(f"/qa/ask/status/{task_id}",
                     headers={"Authorization": "Bearer YOUR_TOKEN"})
```

### High Priority Questions

```python
# Submit high-priority question
response = requests.post("/qa/system/priority-question",
                        json={"question": "Urgent question"},
                        headers={"Authorization": "Bearer YOUR_TOKEN"})
```

### User Analytics

```python
# Get user report
report = requests.get("/qa/user/report?days=30",
                     headers={"Authorization": "Bearer YOUR_TOKEN"})

# Get queue status
queues = requests.get("/qa/system/queues",
                     headers={"Authorization": "Bearer YOUR_TOKEN"})
```

## Monitoring

### Flower Dashboard
Access the Flower monitoring dashboard at: http://localhost:5555

Features:
- Real-time task monitoring
- Worker status and statistics
- Queue lengths and throughput
- Task history and results
- Worker management

### Queue Statistics

```python
# Check queue status
import requests

response = requests.get("/qa/system/queues")
print(response.json())
```

### Task Management

```python
from app.utils.task_monitor import task_monitor

# Get user tasks
user_tasks = task_monitor.get_user_tasks(user_id=1)

# Cancel a task
task_monitor.cancel_task(task_id="abc123", user_id=1)

# Retry a failed task
new_task_id = task_monitor.retry_task(task_id="abc123", user_id=1)

# Get analytics
analytics = task_monitor.get_task_analytics(user_id=1, days=7)
```

## Configuration Options

### Worker Scaling

Adjust worker concurrency based on your system:

```bash
# High-memory system (document processing)
celery worker --concurrency=4 --queues=document_processing

# High-CPU system (question answering)
celery worker --concurrency=8 --queues=question_answering
```

### Rate Limiting

Configure rate limits in settings:

```python
# In config.py
RATE_LIMIT_ENABLED = True
MAX_QUERIES_PER_HOUR = 100
MAX_DOCUMENTS_PER_USER = 50
```

### Task Priorities

Use different queues for priority:

```python
# High priority
task = answer_question_async.apply_async(
    args=[user_id, question],
    queue="high_priority"
)

# Normal priority
task = answer_question_async.delay(user_id, question)
```

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Restart Redis
   sudo systemctl restart redis
   ```

2. **Worker Not Processing Tasks**
   ```bash
   # Check worker logs
   tail -f logs/celery-worker-qa.log
   
   # Restart workers
   ./scripts/stop_celery.sh && ./scripts/start_celery.sh
   ```

3. **High Memory Usage**
   ```bash
   # Reduce worker concurrency
   celery worker --concurrency=1 --max-tasks-per-child=100
   
   # Monitor memory usage
   htop
   ```

4. **Queue Backlog**
   ```bash
   # Purge all queues
   celery -A app.celery_app:celery_app purge
   
   # Scale up workers
   docker-compose up -d --scale celery-worker-qa=5
   ```

### Performance Tuning

1. **Database Connection Pool**
   ```python
   # In config.py
   DATABASE_URL = "postgresql://user:pass@host:5432/db?pool_size=20&max_overflow=30"
   ```

2. **Redis Optimization**
   ```bash
   # In redis.conf
   maxmemory 1gb
   maxmemory-policy allkeys-lru
   save 900 1
   ```

3. **Worker Optimization**
   ```python
   # In celery_app.py
   worker_prefetch_multiplier = 1
   task_acks_late = True
   worker_max_tasks_per_child = 1000
   ```

## Production Deployment

### Docker Swarm
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml qa-service

# Scale services
docker service scale qa-service_celery-worker-qa=5
```

### Kubernetes
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker-qa
spec:
  replicas: 3
  selector:
    matchLabels:
      app: celery-worker-qa
  template:
    metadata:
      labels:
        app: celery-worker-qa
    spec:
      containers:
      - name: worker
        image: qa-service:latest
        command: ["celery", "-A", "app.celery_app:celery_app", "worker", "--queues=question_answering"]
        env:
        - name: CELERY_BROKER_URL
          value: "redis://redis-service:6379/0"
```

### Load Balancing
```nginx
# nginx.conf
upstream qa_backend {
    server web:8000;
}

upstream flower_backend {
    server flower:5555;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://qa_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /flower/ {
        proxy_pass http://flower_backend;
        auth_basic "Flower";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

### Health Checks
```python
# app/health.py
from fastapi import APIRouter
from app.utils.task_monitor import task_monitor
import redis

router = APIRouter()

@router.get("/health/celery")
async def celery_health():
    try:
        # Check Redis connection
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        
        # Check worker availability
        inspect = celery_app.control.inspect()
        active = inspect.active()
        
        if not active:
            return {"status": "unhealthy", "message": "No active workers"}
        
        return {"status": "healthy", "workers": len(active)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Security Considerations

### Redis Security
```bash
# redis.conf
requirepass your_secure_password
protected-mode yes
port 0
unixsocket /tmp/redis.sock
unixsocketperm 700
```

### RabbitMQ Security
```bash
# Create dedicated user
rabbitmqctl add_user qa_user secure_password
rabbitmqctl set_permissions -p / qa_user ".*" ".*" ".*"
rabbitmqctl delete_user guest
```

### Task Security
```python
# Validate user ownership
def secure_task(func):
    def wrapper(self, user_id, *args, **kwargs):
        # Verify user exists and is active
        with get_task_db() as db:
            user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
            if not user:
                raise ValueError("Invalid user")
        return func(self, user_id, *args, **kwargs)
    return wrapper

@celery_app.task(bind=True)
@secure_task
def secure_document_task(self, user_id, data):
    # Task implementation
    pass
```

## Advanced Features

### Custom Task Routing
```python
# app/celery_routing.py
from kombu import Queue

task_routes = {
    'app.tasks.document_tasks.*': {
        'queue': 'document_processing',
        'routing_key': 'document.processing',
    },
    'app.tasks.qa_tasks.answer_question_async': {
        'queue': 'question_answering',
        'routing_key': 'qa.normal',
    },
    'app.tasks.qa_tasks.priority_question': {
        'queue': 'high_priority',
        'routing_key': 'qa.priority',
    }
}

task_queues = (
    Queue('document_processing', routing_key='document.processing'),
    Queue('question_answering', routing_key='qa.normal'),
    Queue('high_priority', routing_key='qa.priority', priority=10),
)
```

### Custom Serialization
```python
# For handling large documents
import pickle
import zlib

def compress_pickle(obj):
    return zlib.compress(pickle.dumps(obj))

def decompress_pickle(compressed):
    return pickle.loads(zlib.decompress(compressed))

# Custom serializer
class CompressedPickleSerializer:
    def dumps(self, obj):
        return compress_pickle(obj)
    
    def loads(self, data):
        return decompress_pickle(data)
```

### Webhook Integration
```python
# app/tasks/webhook_tasks.py
@celery_app.task
def send_completion_webhook(user_id: int, task_id: str, result: dict):
    """Send webhook when task completes"""
    # Get user webhook URL
    webhook_url = get_user_webhook_url(user_id)
    
    if webhook_url:
        payload = {
            "event": "task_completed",
            "task_id": task_id,
            "user_id": user_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            # Log webhook failure
            logger.error(f"Webhook failed for user {user_id}: {e}")
```

## Monitoring and Alerting

### Prometheus Metrics
```python
# app/metrics.py
from prometheus_client import Counter, Histogram, Gauge

TASK_COUNTER = Counter('celery_tasks_total', 'Total tasks', ['task_name', 'status'])
TASK_DURATION = Histogram('celery_task_duration_seconds', 'Task duration', ['task_name'])
QUEUE_SIZE = Gauge('celery_queue_size', 'Queue size', ['queue_name'])

def record_task_metrics(task_name: str, status: str, duration: float):
    TASK_COUNTER.labels(task_name=task_name, status=status).inc()
    TASK_DURATION.labels(task_name=task_name).observe(duration)
```

### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Celery Monitoring",
    "panels": [
      {
        "title": "Task Throughput",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(celery_tasks_total[5m])",
            "legendFormat": "{{task_name}} - {{status}}"
          }
        ]
      },
      {
        "title": "Queue Sizes",
        "type": "singlestat",
        "targets": [
          {
            "expr": "celery_queue_size",
            "legendFormat": "{{queue_name}}"
          }
        ]
      }
    ]
  }
}
```

### Error Tracking
```python
# app/error_tracking.py
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    integrations=[CeleryIntegration()]
)

@celery_app.task(bind=True)
def monitored_task(self):
    try:
        # Task logic
        pass
    except Exception as e:
        # Automatically captured by Sentry
        raise e
```

## Migration Guide

### From Sync to Async

1. **Update API Calls**
   ```python
   # Old sync version
   result = process_document(file_data)
   
   # New async version
   task = process_document_async.delay(file_data)
   result = task.get(timeout=300)  # For immediate result
   # Or poll task.status for progress
   ```

2. **Handle Task States**
   ```python
   # Check task status in frontend
   async function checkTaskStatus(taskId) {
       const response = await fetch(`/qa/upload/status/${taskId}`);
       const data = await response.json();
       
       if (data.status === 'SUCCESS') {
           // Task completed
           handleSuccess(data.result);
       } else if (data.status === 'FAILURE') {
           // Task failed
           handleError(data.result);
       } else {
           // Still processing, check again later
           setTimeout(() => checkTaskStatus(taskId), 2000);
       }
   }
   ```

3. **Update Database Models**
   ```python
   # Add task tracking fields
   class Document(Base):
       # ... existing fields ...
       processing_task_id = Column(String, nullable=True)
       processing_status = Column(String, default="pending")
       processing_error = Column(Text, nullable=True)
   ```

## FAQ

**Q: How do I handle task failures?**
A: Tasks automatically retry on failure. You can also manually retry using the task monitor:
```python
new_task_id = task_monitor.retry_task(failed_task_id, user_id)
```

**Q: Can I cancel running tasks?**
A: Yes, use the task monitor:
```python
success = task_monitor.cancel_task(task_id, user_id)
```

**Q: How do I prioritize certain users?**
A: Use different queues or task priorities:
```python
# Premium user - high priority queue
task = answer_question_async.apply_async(
    args=[user_id, question],
    queue="high_priority"
)
```

**Q: How do I handle large file uploads?**
A: Files are base64 encoded for task serialization. For very large files, consider:
- Storing files in shared storage (S3, NFS)
- Passing file paths instead of content
- Using chunked uploads

**Q: How do I monitor memory usage?**
A: Set worker limits:
```python
# In celery config
worker_max_tasks_per_child = 100  # Restart worker after 100 tasks
worker_max_memory_per_child = 200000  # 200MB limit
```

**Q: How do I backup task data?**
A: Redis data is persisted to disk. For PostgreSQL:
```bash
# Backup
pg_dump qa_db > backup.sql

# Restore
psql qa_db < backup.sql
```

This completes the comprehensive Celery integration for your QA service, providing robust multi-user queue management, scalability, and monitoring capabilities.