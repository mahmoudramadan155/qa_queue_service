import pytest
from fastapi.testclient import TestClient

class TestAuth:
    def test_register_user(self, client: TestClient):
        """Test user registration"""
        response = client.post(
            "/auth/register",
            json={"email": "newuser@example.com", "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "created_at" in data

    def test_register_duplicate_user(self, client: TestClient):
        """Test registering duplicate user fails"""
        user_data = {"email": "duplicate@example.com", "password": "password123"}
        
        # First registration
        response1 = client.post("/auth/register", json=user_data)
        assert response1.status_code == 200
        
        # Second registration should fail
        response2 = client.post("/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "Email already registered" in response2.json()["detail"]

    def test_login_valid_user(self, client: TestClient):
        """Test login with valid credentials"""
        user_data = {"email": "logintest@example.com", "password": "password123"}
        
        # Register user first
        client.post("/auth/register", json=user_data)
        
        # Login
        response = client.post("/auth/login", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_user(self, client: TestClient):
        """Test login with invalid credentials"""
        response = client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_wrong_password(self, client: TestClient):
        """Test login with wrong password"""
        user_data = {"email": "wrongpwtest@example.com", "password": "correctpassword"}
        
        # Register user first
        client.post("/auth/register", json=user_data)
        
        # Login with wrong password
        response = client.post(
            "/auth/login",
            json={"email": "wrongpwtest@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_protected_endpoint_without_token(self, client: TestClient):
        """Test accessing protected endpoint without token"""
        response = client.get("/qa/documents")
        assert response.status_code == 403  # FastAPI HTTPBearer returns 403

    def test_protected_endpoint_with_invalid_token(self, client: TestClient):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/qa/documents", headers=headers)
        assert response.status_code == 401