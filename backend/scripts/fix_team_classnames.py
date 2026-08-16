#!/usr/bin/env python
"""Fix team project className so all teachers can see them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.repositories.json_store import JsonStore

TARGETS = [
    "smart-health-guardian",
    "ai-learning-companion",
    "student-score-warning-system",
    "campus-secondhand-market",
    "student-learning-behavior-analysis",
    "smart-lab-reservation-system",
    "campus-activity-volunteer-system",
]

db = SessionLocal()
try:
    store = JsonStore(db)

    # Print current state
    print("=== Before fix ===")
    projects = store.list_payloads("team_collaboration_git", "project", status="active")
    for p in projects:
        if p["id"] in TARGETS:
            cn = p.get("project", {}).get("className", "?")
            print(f"  {p['id']}: className={cn!r}")

    # Fix: set className to empty string so all teachers can see them
    print("\n=== Fixing ===")
    for p in projects:
        if p["id"] in TARGETS:
            p["project"]["className"] = ""
            owner = p.get("ownerId") or p.get("project", {}).get("createdBy") or ""
            store.upsert(
                "team_collaboration_git",
                "project",
                p["id"],
                p,
                owner_id=owner,
                role="demo_realistic_seed",
                status="active",
            )
            print(f"  {p['id']}: className set to ''")

    # Verify
    print("\n=== After fix ===")
    projects = store.list_payloads("team_collaboration_git", "project", status="active")
    for p in projects:
        if p["id"] in TARGETS:
            cn = p.get("project", {}).get("className", "?")
            print(f"  {p['id']}: className={cn!r}")

    print("\nDone!")
finally:
    db.close()
