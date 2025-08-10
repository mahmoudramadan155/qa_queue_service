import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from io import BytesIO
from app.main import app
from app.database.connection import get_db, Base

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_qa.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def auth_headers(client):
    """Get authentication headers for a test user"""
    # Register and login user
    client.post(
        "/auth/register",
        json={"email": "qatest@example.com", "password": "password123"}
    )
    
    login_response = client.post(
        "/auth/login",
        json={"email": "qatest@example.com", "password": "password123"}
    )
    
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

class TestQA:
    def test_upload_txt_document(self, client, auth_headers):
        """Test uploading a text document"""
        content = "This is a test document. It contains some sample text for testing."
        files = {"file": ("test.txt", BytesIO(content.encode()), "text/plain")}
        
        response = client.post("/qa/upload", files=files, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["chunk_count"] > 0
        assert "content_hash" in data

    def test_upload_unsupported_file(self, client, auth_headers):
        """Test uploading unsupported file type"""
        content = "test content"
        files = {"file": ("test.docx", BytesIO(content.encode()), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        response = client.post("/qa/upload", files=files, headers=auth_headers)
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    def test_upload_duplicate_document(self, client, auth_headers):
        """Test uploading duplicate document"""
        content = "This is a duplicate test document."
        files = {"file": ("duplicate.txt", BytesIO(content.encode()), "text/plain")}
        
        # First upload
        response1 = client.post("/qa/upload", files=files, headers=auth_headers)
        assert response1.status_code == 200
        
        # Second upload (same content)
        files = {"file": ("duplicate2.txt", BytesIO(content.encode()), "text/plain")}
        response2 = client.post("/qa/upload", files=files, headers=auth_headers)
        assert response2.status_code == 400
        assert "identical content" in response2.json()["detail"]

    def test_ask_question_without_documents(self, client, auth_headers):
        """Test asking question when no documents uploaded"""
        response = client.post(
            "/qa/ask",
            json={"question": "What is this about?"},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "don't have enough information" in data["answer"].lower()

    def test_ask_question_with_document(self, client, auth_headers):
        """Test asking question with uploaded document"""
        # Upload document first
        content = "Python is a high-level programming language. It is widely used for web development, data analysis, and artificial intelligence."
        files = {"file": ("python_info.txt", BytesIO(content.encode()), "text/plain")}
        client.post("/qa/upload", files=files, headers=auth_headers)
        
        # Ask question
        response = client.post(
            "/qa/ask",
            json={"question": "What is Python used for?"},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "question" in data
        assert "answer" in data
        assert "response_time_ms" in data
        assert len(data["answer"]) > 0

    def test_ask_empty_question(self, client, auth_headers):
        """Test asking empty question"""
        response = client.post(
            "/qa/ask",
            json={"question": "   "},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def test_list_documents(self, client, auth_headers):
        """Test listing user documents"""
        # Upload a document first
        content = "Test document for listing"
        files = {"file": ("list_test.txt", BytesIO(content.encode()), "text/plain")}
        client.post("/qa/upload", files=files, headers=auth_headers)
        
        # List documents
        response = client.get("/qa/documents", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check document structure
        doc = data[0]
        assert "id" in doc
        assert "filename" in doc
        assert "chunk_count" in doc
        assert "created_at" in doc

    def test_delete_document(self, client, auth_headers):
        """Test deleting a document"""
        # Upload document first
        content = "Document to be deleted"
        files = {"file": ("delete_test.txt", BytesIO(content.encode()), "text/plain")}
        upload_response = client.post("/qa/upload", files=files, headers=auth_headers)
        
        # Get document ID from the list
        docs_response = client.get("/qa/documents", headers=auth_headers)
        doc_id = docs_response.json()[-1]["id"]  # Get the last uploaded document
        
        # Delete document
        response = client.delete(f"/qa/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_nonexistent_document(self, client, auth_headers):
        """Test deleting non-existent document"""
        response = client.delete("/qa/documents/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_query_history(self, client, auth_headers):
        """Test getting query history"""
        # Ask a question to create history
        client.post(
            "/qa/ask",
            json={"question": "Test question for history"},
            headers=auth_headers
        )
        
        # Get history
        response = client.get("/qa/history", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            query = data[0]
            assert "id" in query
            assert "question" in query
            assert "answer" in query
            assert "response_time" in query
            assert "created_at" in query