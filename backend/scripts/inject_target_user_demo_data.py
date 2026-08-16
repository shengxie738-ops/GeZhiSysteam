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
from app.demo_data.target_user_demo_seed import seed_target_user_demo_data


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
    parser = argparse.ArgumentParser(description="Inject realistic demo data for user 23001020119 into the configured database.")
    parser.add_argument("--data-root", default=r"D:\软件杯测试数据注入", help="Folder containing 学生姓名.txt and 头像/*.jpg")
    parser.add_argument("--static-root", default=str(BACKEND_ROOT / "app" / "static"), help="Backend static folder for avatars and repository zip files")
    parser.add_argument("--anchor-date", default=None, help="ISO timestamp used as the deterministic data clock")
    parser.add_argument("--reset-target", action="store_true", help="Remove this target user's previous injected records before writing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = seed_target_user_demo_data(
            db,
            data_root=args.data_root,
            static_root=args.static_root,
            anchor_now=_parse_anchor(args.anchor_date),
            reset_target=args.reset_target,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
