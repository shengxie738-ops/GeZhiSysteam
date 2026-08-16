from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from app.core.database import SessionLocal
from app.demo_data.target_teacher_homework_seed import seed_target_teacher_homework_data


def _parse_anchor(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Su teacher and publish extra demo homeworks for student 23001020119.")
    parser.add_argument(
        "--teacher-root",
        default=r"D:\演示账号的同学文件\团队仓库测试\教师账户",
        help="Folder containing teacher avatar file 头像.jpg",
    )
    parser.add_argument(
        "--static-root",
        default=str(BACKEND_ROOT / "app" / "static"),
        help="Backend static folder for copied avatars",
    )
    parser.add_argument("--anchor-date", default=None, help="ISO timestamp used as the deterministic data clock")
    parser.add_argument("--reset-homeworks", action="store_true", help="Remove previous Su teacher seeded homeworks before writing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = seed_target_teacher_homework_data(
            db,
            teacher_root=args.teacher_root,
            static_root=args.static_root,
            anchor_now=_parse_anchor(args.anchor_date),
            reset_homeworks=args.reset_homeworks,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
