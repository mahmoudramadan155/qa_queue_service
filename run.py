#!/usr/bin/env python3
"""
Startup script for the AI Question-Answering Service
"""
import uvicorn
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import settings

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs(settings.chroma_persist_directory, exist_ok=True)
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8009,
        # reload=True,
        log_level=settings.log_level.lower()
    )