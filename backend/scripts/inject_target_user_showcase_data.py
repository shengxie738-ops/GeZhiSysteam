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
from app.demo_data.target_user_showcase_seed import seed_target_user_showcase_data


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
    parser = argparse.ArgumentParser(description="Inject polished showcase data for target student account 23001020119.")
    parser.add_argument("--classmates-root", default=r"D:\演示账号的同学文件", help="Folder containing 演示账号的同学用户.txt and 同学头像")
    parser.add_argument("--team-repo-root", default=r"D:\团队仓库数据", help="Folder containing OJ Review and RAG Course repositories")
    parser.add_argument("--static-root", default=str(BACKEND_ROOT / "app" / "static"), help="Backend static folder for avatars and repository archives")
    parser.add_argument("--anchor-date", default=None, help="ISO timestamp used as the deterministic data clock")
    parser.add_argument("--reset-target", action="store_true", help="Remove target showcase records before writing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = seed_target_user_showcase_data(
            db,
            classmates_root=args.classmates_root,
            team_repo_root=args.team_repo_root,
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
