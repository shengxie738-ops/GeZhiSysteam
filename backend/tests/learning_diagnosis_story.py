import json
import requests
from pathlib import Path


base = "http://127.0.0.1:8516/api/learning-diagnosis"
s = requests.Session()
s.headers["Authorization"] = f"Bearer {(Path(__file__).resolve().parents[2] / 'artifacts' / 'qa_token_story.txt').read_text(encoding='utf-8')}"
created = s.post(base + "/sessions", json={"student_id": "story-student", "course": "数据结构", "weekly_minutes": 180, "include_git_evidence": False}, timeout=30)
print("create", created.status_code)
data = created.json().get("data", {})
session = data.get("session", {})
path = data.get("path", {})
snapshot = data.get("snapshot", {})
print(json.dumps({"session_id": session.get("id"), "snapshot_id": snapshot.get("id"), "snapshot_version": snapshot.get("version"), "path_version": path.get("path_version"), "practice_score": snapshot.get("assessments", [{}])[0].get("practice_score")}, ensure_ascii=False))
session_id = session["id"]
task_id = path["tasks"][2]["task_id"]
print("path", s.get(base + f"/sessions/{session_id}/path", params={"student_id": "story-student"}).status_code)
hint = s.post(base + f"/tasks/{task_id}/hints", params={"session_id": session_id, "student_id": "story-student"}, json={"requested_level": 5, "assessment_mode": True}, timeout=30)
print("hint", hint.status_code, hint.json().get("data"))
submit = s.post(base + f"/tasks/{task_id}/submit", json={"student_id": "story-student", "session_id": session_id, "code": "print('ok')", "hint_level": 1, "assessment_mode": True}, timeout=30)
print("submit", submit.status_code)
submitted = submit.json().get("data", {})
print(json.dumps({"status": submitted.get("status"), "execution_status": submitted.get("execution", {}).get("status"), "execution_id": submitted.get("execution_id"), "snapshot_version": submitted.get("snapshot", {}).get("version"), "path_version": submitted.get("path", {}).get("path_version")}, ensure_ascii=False))
print("snapshot", s.get(base + f"/snapshots/{submitted.get('snapshot', {}).get('id')}", params={"student_id": "story-student"}).status_code)
