#!/usr/bin/env python
"""Verify injected team repos in database and Gitea."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from app.core.database import SessionLocal
from app.repositories.json_store import JsonStore

GITEA_BASE_URL = "http://127.0.0.1:3000"
GITEA_TOKEN = "5ec8ff0a1e13d677b8cca4ca02c20c111f900008"
GITEA_ORG = "campus"

TARGETS = [
    "smart-health-guardian",
    "ai-learning-companion",
    "student-score-warning-system",
    "campus-secondhand-market",
    "student-learning-behavior-analysis",
    "smart-lab-reservation-system",
    "campus-activity-volunteer-system",
]


def verify_database():
    print("=" * 60)
    print("[Database] Team Collaboration Projects")
    print("=" * 60)
    db = SessionLocal()
    try:
        store = JsonStore(db)
        projects = store.list_payloads("team_collaboration_git", "project", status="active")
        print(f"Total active team projects: {len(projects)}\n")

        for p in projects:
            proj = p.get("project", {})
            repo = p.get("repository", {})
            members = p.get("memberProgress", [])
            member_names = [m.get("name") for m in members]
            print(f"  ID: {p.get('id')}")
            print(f"  Title: {proj.get('title')}")
            print(f"  Team: {proj.get('teamName')}")
            print(f"  Course: {proj.get('course')}")
            print(f"  Repo: {repo.get('repoName')} (status={repo.get('status')})")
            print(f"  Gitea: {repo.get('htmlUrl')}")
            print(f"  Members ({len(members)}): {', '.join(member_names)}")
            for m in members:
                print(f"    - {m.get('name')} ({m.get('role')}): progress={m.get('progress')}%, commits={m.get('commitCount')}, status={m.get('statusLabel')}")
            print()
    finally:
        db.close()


def verify_gitea():
    print("=" * 60)
    print("[Gitea] Repository Status")
    print("=" * 60)
    headers = {"Authorization": f"token {GITEA_TOKEN}"}
    for name in TARGETS:
        r = requests.get(f"{GITEA_BASE_URL}/api/v1/repos/{GITEA_ORG}/{name}", headers=headers)
        if r.status_code == 200:
            data = r.json()
            empty = data.get("empty", True)
            size = data.get("size", 0)
            branch = data.get("default_branch", "?")
            print(f"  {name}: empty={empty}, size={size}KB, branch={branch}")
        else:
            print(f"  {name}: NOT FOUND ({r.status_code})")

    # Check collaborators on first repo
    print()
    print("  Collaborators on smart-health-guardian:")
    r = requests.get(
        f"{GITEA_BASE_URL}/api/v1/repos/{GITEA_ORG}/smart-health-guardian/collaborators",
        headers=headers,
    )
    if r.status_code == 200:
        collabs = r.json()
        for c in collabs:
            print(f"    - {c.get('login')} ({c.get('full_name')})")


if __name__ == "__main__":
    verify_database()
    print()
    verify_gitea()
