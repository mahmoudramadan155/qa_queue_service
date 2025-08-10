import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Add the parent directory to Python path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database.connection import get_db, Base

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def test_app():
    """Create test FastAPI app"""
    return app

@pytest.fixture(scope="session") 
def client(test_app):
    """Create test client"""
    # Create test database tables
    Base.metadata.create_all(bind=engine)
    
    with TestClient(test_app) as c:
        yield c
    
    # Clean up - remove test database
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test.db"):
        os.remove("test.db")

@pytest.fixture
def auth_headers(client):
    """Get authentication headers for a test user"""
    # Register and login user
    register_data = {
        "email": "test@example.com", 
        "password": "testpassword123"
    }
    
    # Try to register (might already exist)
    client.post("/auth/register", json=register_data)
    
    # Login to get token
    login_response = client.post("/auth/login", json=register_data)
    
    if login_response.status_code != 200:
        pytest.fail(f"Failed to login: {login_response.text}")
    
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}