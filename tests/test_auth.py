import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database.connection import get_db, Base
from app.config import settings

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    # Create test database tables
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    # Clean up
    Base.metadata.drop_all(bind=engine)

class TestAuth:
    def test_register_user(self, client):
        """Test user registration"""
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "created_at" in data

    def test_register_duplicate_user(self, client):
        """Test registering duplicate user fails"""
        # First registration
        client.post(
            "/auth/register",
            json={"email": "duplicate@example.com", "password": "password123"}
        )
        
        # Second registration should fail
        response = client.post(
            "/auth/register",
            json={"email": "duplicate@example.com", "password": "password123"}
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_login_valid_user(self, client):
        """Test login with valid credentials"""
        # Register user first
        client.post(
            "/auth/register",
            json={"email": "login@example.com", "password": "password123"}
        )
        
        # Login
        response = client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_user(self, client):
        """Test login with invalid credentials"""
        response = client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_wrong_password(self, client):
        """Test login with wrong password"""
        # Register user first
        client.post(
            "/auth/register",
            json={"email": "wrongpw@example.com", "password": "correctpassword"}
        )
        
        # Login with wrong password
        response = client.post(
            "/auth/login",
            json={"email": "wrongpw@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/qa/documents")
        assert response.status_code == 403  # FastAPI HTTPBearer returns 403

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/qa/documents", headers=headers)
        assert response.status_code == 401
