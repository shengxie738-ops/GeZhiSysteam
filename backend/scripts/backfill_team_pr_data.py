#!/usr/bin/env python
"""Backfill training-team Pull Request rows from member Git progress."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.services.team_git_service import backfill_training_pull_request_records


def main() -> int:
    db = SessionLocal()
    try:
        changed = backfill_training_pull_request_records(db)
        print(f"Backfilled PR data for {changed} training team project(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
