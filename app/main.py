from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager
import uvicorn
import os

from app.config import settings
from app.database.connection import engine
from app.database.models import Base
from app.auth.routes import router as auth_router
from app.qa.routes import router as qa_router
from app.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up AI Question-Answering Service")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Question-Answering Service")

# Create FastAPI app
app = FastAPI(
    title="AI Question-Answering Service",
    description="A complete AI-powered question-answering API with vector database integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory if it doesn't exist and mount it
if not os.path.exists("static"):
    os.makedirs("static")
    logger.info("Created static directory")

# Only mount static files if directory exists and has files
if os.path.exists("static") and os.listdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted")

# Include routers
app.include_router(auth_router)
app.include_router(qa_router)

@app.get("/")
async def root():
    """Root endpoint - serve the frontend"""
    
    if os.path.exists("static/index.html"):
        return FileResponse('static/index.html')

        # Otherwise, provide a simple HTML page with links
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Question-Answering Service</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .header { text-align: center; margin-bottom: 40px; }
            .links { display: flex; justify-content: center; gap: 20px; margin: 30px 0; }
            .btn { padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            .btn:hover { background: #0056b3; }
            .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 AI Question-Answering Service</h1>
            <p>A complete AI-powered question-answering API with vector database integration</p>
        </div>
        
        <div class="links">
            <a href="/docs" class="btn">📚 API Documentation (Swagger)</a>
            <a href="/redoc" class="btn">📖 API Documentation (ReDoc)</a>
            <a href="/health" class="btn">💚 Health Check</a>
        </div>
        
        <h2>🚀 Quick Start</h2>
        <div class="endpoint">
            <strong>1. Register:</strong> POST /auth/register<br>
            <code>{"email": "user@example.com", "password": "password123"}</code>
        </div>
        
        <div class="endpoint">
            <strong>2. Login:</strong> POST /auth/login<br>
            <code>{"email": "user@example.com", "password": "password123"}</code>
        </div>
        
        <div class="endpoint">
            <strong>3. Upload Document:</strong> POST /qa/upload<br>
            <code>Form data with file field (PDF/TXT)</code>
        </div>
        
        <div class="endpoint">
            <strong>4. Ask Question:</strong> POST /qa/ask<br>
            <code>{"question": "What is this document about?"}</code>
        </div>
        
        <p><strong>Note:</strong> All endpoints except auth require Authorization header: <code>Bearer YOUR_TOKEN</code></p>
    </body>
    </html>
    """, status_code=200)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Question-Answering Service",
        "version": "1.0.0"
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify API functionality"""
    return {
        "message": "API is working!",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc", 
            "health": "/health",
            "auth": "/auth/register, /auth/login",
            "qa": "/qa/upload, /qa/ask, /qa/documents, /qa/history"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8009)
