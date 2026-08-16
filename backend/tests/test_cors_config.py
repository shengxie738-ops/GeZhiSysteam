import os

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from app.core.config import parse_cors_origins


def test_default_cors_origins_include_static_student_frontend_ports():
    origins = parse_cors_origins("")

    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:5174" in origins
    assert "http://127.0.0.1:5174" in origins


def test_cors_origins_accept_json_and_csv_without_trailing_slashes():
    assert parse_cors_origins('["https://example.edu/","https://git.example.edu"]') == [
        "https://example.edu",
        "https://git.example.edu",
    ]
    assert parse_cors_origins("https://a.example/, https://b.example") == [
        "https://a.example",
        "https://b.example",
    ]
