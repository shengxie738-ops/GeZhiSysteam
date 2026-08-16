"""为演示账号 23001020119 注入六维图谱数据并验证雷达数值。

用法：python scripts/inject_target_user_sixdim_data.py
幂等，可重复执行。验证环节直接调用教师端/学生端同源的
_compute_radar_values，确保注入的是后端真实数据而非前端演示数据。
"""

from __future__ import annotations

import json
import os
import sys
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

from app.core.database import SessionLocal  # noqa: E402
from app.demo_data.target_user_sixdim_seed import seed_target_user_sixdim_data  # noqa: E402


def verify_radar(db) -> dict:
    from app.api.endpoints.analytics import _compute_radar_values
    from app.models.student_profile import StudentProfile
    from app.models.user_account import UserAccount
    from app.repositories.json_store import JsonStore

    account = db.query(UserAccount).filter(UserAccount.username == "23001020119").first()
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == "23001020119").first()
    metrics = _compute_radar_values(
        "23001020119",
        (account.real_name if account else None) or "23001020119",
        profile,
        JsonStore(db),
    )
    return {
        "radarValues": metrics["radarValues"],
        "radarEvidence": {key: value["label"] for key, value in metrics["radarEvidence"].items()},
        "homeworkAvg": metrics["homeworkAvg"],
        "examAvg": metrics["examAvg"],
        "errorCount": metrics["errorCount"],
        "unmasteredCount": metrics["unmasteredCount"],
        "forumCount": metrics["forumCount"],
        "checkpointRate": metrics["checkpointRate"],
    }


def main() -> int:
    db = SessionLocal()
    try:
        summary = seed_target_user_sixdim_data(db)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("\n=== 六维雷达验证（后端同源计算） ===")
        print(json.dumps(verify_radar(db), ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
