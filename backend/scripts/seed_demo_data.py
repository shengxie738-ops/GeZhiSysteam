from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.demo_data.realistic_seed import seed_realistic_demo_data
from app.demo_data.target_user_demo_seed import seed_target_user_demo_data


def main() -> None:
    db = SessionLocal()
    try:
        realistic = seed_realistic_demo_data(db)
        target = seed_target_user_demo_data(db)
        print({"realistic": realistic.get("gitea_accounts"), "target": target.get("gitea_accounts")})
    finally:
        db.close()


if __name__ == "__main__":
    main()
