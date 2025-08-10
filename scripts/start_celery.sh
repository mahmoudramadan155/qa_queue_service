#!/bin/bash
# scripts/start_celery.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Celery Services for QA System${NC}"

# Check if Redis is running
echo -e "${YELLOW}Checking Redis connection...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}✗ Redis is not running. Please start Redis first.${NC}"
    echo "Start Redis with: redis-server"
    exit 1
fi

# Create necessary directories
mkdir -p logs
mkdir -p tmp

# Function to start a service
start_service() {
    local service_name=$1
    local command=$2
    local log_file="logs/${service_name}.log"
    
    echo -e "${YELLOW}Starting ${service_name}...${NC}"
    nohup $command > $log_file 2>&1 &
    echo $! > "tmp/${service_name}.pid"
    echo -e "${GREEN}✓ ${service_name} started (PID: $(cat tmp/${service_name}.pid))${NC}"
}

# Start Celery Workers
echo -e "\n${YELLOW}Starting Celery Workers...${NC}"

# Document Processing Worker
start_service "celery-worker-docs" \
    "celery -A app.celery_app:celery_app worker --loglevel=info --queues=document_processing --concurrency=2 --hostname=worker-docs@%h"

# Question Answering Worker
start_service "celery-worker-qa" \
    "celery -A app.celery_app:celery_app worker --loglevel=info --queues=question_answering,high_priority --concurrency=4 --hostname=worker-qa@%h"

# User Management Worker
start_service "celery-worker-users" \
    "celery -A app.celery_app:celery_app worker --loglevel=info --queues=user_management --concurrency=2 --hostname=worker-users@%h"

# Start Celery Beat (Scheduler)
echo -e "\n${YELLOW}Starting Celery Beat Scheduler...${NC}"
start_service "celery-beat" \
    "celery -A app.celery_app:celery_app beat --loglevel=info --schedule=tmp/celerybeat-schedule --pidfile=tmp/celerybeat.pid"

# Start Flower (Monitoring)
echo -e "\n${YELLOW}Starting Flower Monitoring...${NC}"
start_service "flower" \
    "celery -A app.celery_app:celery_app flower --port=5555"

echo -e "\n${GREEN}All Celery services started successfully!${NC}"
echo -e "${YELLOW}Services:${NC}"
echo "  • Document Processing Worker: PID $(cat tmp/celery-worker-docs.pid)"
echo "  • Question Answering Worker: PID $(cat tmp/celery-worker-qa.pid)"
echo "  • User Management Worker: PID $(cat tmp/celery-worker-users.pid)"
echo "  • Beat Scheduler: PID $(cat tmp/celery-beat.pid)"
echo "  • Flower Monitoring: PID $(cat tmp/flower.pid)"

echo -e "\n${YELLOW}Monitoring:${NC}"
echo "  • Flower UI: http://localhost:5555"
echo "  • Logs directory: ./logs/"

echo -e "\n${YELLOW}To stop all services, run:${NC} ./scripts/stop_celery.sh"

# Show status
echo -e "\n${YELLOW}Current Status:${NC}"
./scripts/celery_status.sh