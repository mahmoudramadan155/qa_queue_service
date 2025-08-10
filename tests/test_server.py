from fastapi import FastAPI

# Simple FastAPI app to test docs
app = FastAPI(
    title="Test API",
    description="Simple test to verify Swagger UI works",
    version="1.0.0"
)

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "Hello World"}

@app.get("/test")
def test():
    """Test endpoint"""
    return {"status": "working"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)