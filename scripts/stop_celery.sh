#!/bin/bash
# scripts/stop_celery.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}Stopping Celery Services for QA System${NC}"

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="tmp/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo -e "${YELLOW}Stopping ${service_name} (PID: $pid)...${NC}"
        
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid"
            sleep 2
            
            # Check if process is still running
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${YELLOW}Force killing ${service_name}...${NC}"
                kill -KILL "$pid"
            fi
            
            echo -e "${GREEN}✓ ${service_name} stopped${NC}"
        else
            echo -e "${YELLOW}⚠ ${service_name} was not running${NC}"
        fi
        
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}⚠ No PID file found for ${service_name}${NC}"
    fi
}

# Stop all services
echo -e "\n${YELLOW}Stopping Celery Workers and Services...${NC}"

stop_service "celery-worker-docs"
stop_service "celery-worker-qa"
stop_service "celery-worker-users"
stop_service "celery-beat"
stop_service "flower"

# Clean up any remaining Celery processes
echo -e "\n${YELLOW}Cleaning up any remaining Celery processes...${NC}"
pkill -f "celery.*worker" 2>/dev/null || true
pkill -f "celery.*beat" 2>/dev/null || true
pkill -f "celery.*flower" 2>/dev/null || true

echo -e "\n${GREEN}All Celery services stopped successfully!${NC}"

# Clean up temporary files
echo -e "${YELLOW}Cleaning up temporary files...${NC}"
rm -f tmp/celerybeat-schedule*
rm -f tmp/celerybeat.pid

echo -e "${GREEN}✓ Cleanup completed${NC}"