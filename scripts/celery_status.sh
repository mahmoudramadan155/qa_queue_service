#!/bin/bash
# scripts/celery_status.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Celery Services Status for QA System${NC}"
echo "=================================="

# Function to check service status
check_service() {
    local service_name=$1
    local pid_file="tmp/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}✓ ${service_name}: Running (PID: $pid)${NC}"
        else
            echo -e "${RED}✗ ${service_name}: Not running (stale PID file)${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${RED}✗ ${service_name}: Not running${NC}"
    fi
}

# Check Redis connection
echo -e "\n${YELLOW}Infrastructure Status:${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis: Connected${NC}"
else
    echo -e "${RED}✗ Redis: Not connected${NC}"
fi

# Check database connection (if PostgreSQL)
if command -v psql > /dev/null 2>&1; then
    if psql "$DATABASE_URL" -c '\q' 2>/dev/null; then
        echo -e "${GREEN}✓ Database: Connected${NC}"
    else
        echo -e "${YELLOW}⚠ Database: Connection check skipped${NC}"
    fi
fi

# Check services
echo -e "\n${YELLOW}Celery Services:${NC}"
check_service "celery-worker-docs"
check_service "celery-worker-qa"
check_service "celery-worker-users"
check_service "celery-beat"
check_service "flower"

# Show queue statistics using Celery inspect
echo -e "\n${YELLOW}Queue Statistics:${NC}"
if command -v celery > /dev/null 2>&1; then
    echo "Active tasks:"
    celery -A app.celery_app:celery_app inspect active 2>/dev/null | grep -E "(worker|task)" || echo "  No active tasks"
    
    echo -e "\nQueue lengths:"
    celery -A app.celery_app:celery_app inspect active_queues 2>/dev/null | grep -E "(name|length)" || echo "  Unable to retrieve queue info"
    
    echo -e "\nRegistered tasks:"
    celery -A app.celery_app:celery_app inspect registered 2>/dev/null | head -20 || echo "  Unable to retrieve task info"
else
    echo "  Celery command not available"
fi

# Show recent log entries
echo -e "\n${YELLOW}Recent Log Entries:${NC}"
if [ -d "logs" ]; then
    for log_file in logs/*.log; do
        if [ -f "$log_file" ]; then
            echo -e "${BLUE}$(basename "$log_file"):${NC}"
            tail -3 "$log_file" 2>/dev/null | sed 's/^/  /' || echo "  No recent entries"
        fi
    done
else
    echo "  No log directory found"
fi

# Show system resources
echo -e "\n${YELLOW}System Resources:${NC}"
if command -v free > /dev/null 2>&1; then
    echo "Memory usage:"
    free -h | grep -E "(Mem|Swap)" | sed 's/^/  /'
fi

if command -v df > /dev/null 2>&1; then
    echo "Disk usage:"
    df -h . | tail -1 | sed 's/^/  /'
fi

echo -e "\n${YELLOW}Useful Commands:${NC}"
echo "  Start services: ./scripts/start_celery.sh"
echo "  Stop services:  ./scripts/stop_celery.sh"
echo "  View logs:      tail -f logs/<service>.log"
echo "  Flower UI:      http://localhost:5555"
echo "  Purge queues:   celery -A app.celery_app:celery_app purge"