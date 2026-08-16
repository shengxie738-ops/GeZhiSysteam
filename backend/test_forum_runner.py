from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

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

# We do NOT override get_current_user initially to test 401
client = TestClient(app)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def test_delete_post_unauthorized():
    print("Testing delete post unauthorized...")
    response = client.delete("/api/forum/posts/some_id")
    if response.status_code != 401:
        print(f"FAILED: Expected 401, got {response.status_code}")
        return False
    print("Passed.")
    return True

def test_create_post_payload_overwrite():
    print("Testing create post payload overwrite...")
    app.dependency_overrides[get_current_user] = override_get_current_user
    payload = {
        "title": "Test Post",
        "content": "This is a test post.",
        "category": "qna",
        "likes": 9999,
        "views": 9999,
        "createdAt": "2020-01-01T00:00:00Z"
    }
    response = client.post("/api/forum/posts", json=payload)
    if response.status_code != 200:
        print(f"FAILED: Create post failed {response.status_code} {response.text}")
        return False
    data = response.json().get("data", {})
    if data.get("likes") == 9999:
        print("FAILED: Payload overwrite vulnerability exists (likes=9999)")
        return False
    print("Passed.")
    return True

def test_forum_like_api():
    print("Testing forum like API...")
    post_res = client.post("/api/forum/posts", json={"title": "Like me"})
    if post_res.status_code != 200:
        return False
    post_id = post_res.json()["data"]["id"]
    
    like_res = client.put(f"/api/forum/posts/{post_id}/like")
    if like_res.status_code != 200:
        print(f"FAILED: Like API returned {like_res.status_code}")
        return False
    print("Passed.")
    return True

def test_forum_view_api():
    print("Testing forum view API...")
    post_res = client.post("/api/forum/posts", json={"title": "View me"})
    post_id = post_res.json()["data"]["id"]
    
    view_res = client.put(f"/api/forum/posts/{post_id}/view")
    if view_res.status_code != 200:
        print(f"FAILED: View API returned {view_res.status_code}")
        return False
    print("Passed.")
    return True

if __name__ == "__main__":
    success = True
    success &= test_delete_post_unauthorized()
    success &= test_create_post_payload_overwrite()
    success &= test_forum_like_api()
    success &= test_forum_view_api()
    
    if not success:
        print("\\nSOME TESTS FAILED")
        sys.exit(1)
    print("\\nALL TESTS PASSED")
    sys.exit(0)
