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
from app.demo_data.academic_forum_showcase_seed import seed_academic_forum_showcase_data


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
    parser = argparse.ArgumentParser(description="Inject academic forum showcase posts for the student demo accounts.")
    parser.add_argument(
        "--accounts-file",
        default=r"D:\演示账号的同学文件\演示账号的同学用户.txt",
        help="UTF-8 text file containing demo student names, student IDs, and passwords.",
    )
    parser.add_argument("--anchor-date", default=None, help="ISO timestamp used as the deterministic data clock.")
    parser.add_argument("--reset-forum-showcase", action="store_true", help="Remove previous forum-showcase records first.")
    parser.add_argument("--dry-run", action="store_true", help="Build and validate the dataset without writing records.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = seed_academic_forum_showcase_data(
            db,
            accounts_file=args.accounts_file,
            anchor_now=_parse_anchor(args.anchor_date),
            reset_forum_showcase=args.reset_forum_showcase,
            dry_run=args.dry_run,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
