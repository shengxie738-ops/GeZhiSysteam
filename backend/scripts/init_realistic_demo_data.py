from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.demo_data.realistic_seed import seed_realistic_demo_data


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
    parser = argparse.ArgumentParser(description="初始化真实感 MySQL 演示数据")
    parser.add_argument("--data-root", default=r"D:\软件杯测试数据注入", help="包含 学生姓名.txt 和 头像 文件夹的数据目录")
    parser.add_argument("--static-root", default=str(BACKEND_ROOT / "app" / "static"), help="后端 static 目录")
    parser.add_argument("--anchor-date", default=None, help="时间线锚点，例如 2026-07-05T10:00:00+08:00")
    parser.add_argument("--reset-demo", action="store_true", help="先清理 demo-* 命名空间的演示业务数据")
    parser.add_argument("--dry-run", action="store_true", help="只统计将要生成的数据，不写入数据库")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = seed_realistic_demo_data(
            db,
            data_root=args.data_root,
            static_root=args.static_root,
            anchor_now=_parse_anchor(args.anchor_date),
            reset_demo=args.reset_demo,
            dry_run=args.dry_run,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if args.dry_run:
            print("dry-run 完成，未写入数据库。")
        else:
            print("真实感演示数据初始化完成。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
