from sqlalchemy import inspect, text

from app.core.database import Base, SessionLocal, engine
from app.models import chat_message, code_diagnosis, domain_record, gitea_account_binding, ranked_question, sms_verification_code, student_profile, user_account, user_knowledge, user_rag  # noqa: F401


USER_ACCOUNT_COLUMNS = {
    "role": "VARCHAR(32) NOT NULL DEFAULT 'student'",
    "phone": "VARCHAR(32) NOT NULL DEFAULT ''",
    "real_name": "VARCHAR(100) NOT NULL DEFAULT ''",
    "student_id": "VARCHAR(50) NOT NULL DEFAULT ''",
    "teacher_id": "VARCHAR(64) NOT NULL DEFAULT ''",
    "class_name": "VARCHAR(100) NOT NULL DEFAULT ''",
    "avatar_path": "VARCHAR(512) NOT NULL DEFAULT ''",
}


def _ensure_columns(table_name: str, columns: dict[str, str]) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        return

    existing = {column["name"] for column in inspector.get_columns(table_name)}
    missing = [(name, definition) for name, definition in columns.items() if name not in existing]
    if not missing:
        return

    with engine.begin() as conn:
        for name, definition in missing:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {definition}"))


def _sync_domain_payloads() -> None:
    from app.services.team_git_service import backfill_repository_home_records

    db = SessionLocal()
    try:
        backfill_repository_home_records(db)
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_columns("user_accounts", USER_ACCOUNT_COLUMNS)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE user_accounts MODIFY COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''"))
    _sync_domain_payloads()
