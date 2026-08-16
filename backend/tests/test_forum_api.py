import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.api.endpoints.auth import get_current_user

# Setup test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_forum.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_get_current_user():
    return {"username": "test_user", "role": "student"}

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_post_payload_overwrite():
    # Attempt to overwrite likes and views via payload
    payload = {
        "title": "Test Post",
        "content": "This is a test post.",
        "category": "qna",
        "likes": 9999,
        "views": 9999,
        "createdAt": "2020-01-01T00:00:00Z"
    }
    response = client.post("/api/forum/posts", json=payload)
    assert response.status_code == 200
    data = response.json().get("data", {})
    
    assert data["title"] == "Test Post"
    assert data["likes"] == 0
    assert data["views"] == 1
    assert data["createdAt"] != "2020-01-01T00:00:00Z"

def test_forum_like_api():
    # 1. Create a post
    post_res = client.post("/api/forum/posts", json={"title": "Like me"})
    post_id = post_res.json()["data"]["id"]
    
    # 2. Like the post
    like_res = client.put(f"/api/forum/posts/{post_id}/like")
    assert like_res.status_code == 200
    assert like_res.json()["data"]["likes"] == 1
    
    # 3. View the post
    view_res = client.put(f"/api/forum/posts/{post_id}/view")
    assert view_res.status_code == 200
    assert view_res.json()["data"]["views"] == 2  # initially 1
    
def test_delete_post_unauthorized():
    # Remove auth override to test 401
    app.dependency_overrides.pop(get_current_user)
    response = client.delete("/api/forum/posts/some_id")
    # Should be 401 Unauthorized
    assert response.status_code == 401
    # Restore for other tests
    app.dependency_overrides[get_current_user] = override_get_current_user
