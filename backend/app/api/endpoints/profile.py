from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.miniprogram_response import api_response, is_miniprogram_client, isoformat_z
from app.models.student_profile import StudentProfile
from app.models.user_account import UserAccount

router = APIRouter()

class ProfileUpdate(BaseModel):
    user_id: str
    knowledge: Optional[int] = None
    cognitive: Optional[str] = None
    pace: Optional[int] = None
    error_pattern: Optional[str] = None
    goal: Optional[str] = None
    background: Optional[str] = None

class TestResultRecord(BaseModel):
    user_id: str
    problem_id: str
    category: str  # e.g., '数组与链表', '栈与队列', '树与二叉树'
    status: str    # 'passed' or 'failed'
    difficulty: str # 'Easy', 'Medium', 'Hard'
    error_msg: Optional[str] = None

def _profile_payload(profile: StudentProfile, account: UserAccount | None = None) -> dict:
    return {
        "user_id": profile.user_id,
        "name": (account.real_name if account else "") or profile.user_id,
        "class_name": (account.class_name if account else "") or "",
        "avatar_url": f"/static/avatars/{account.avatar_path}" if account and account.avatar_path else "",
        "behavior": {
            "knowledge": int(profile.knowledge or 50),
            "cognitive": profile.cognitive or "娓愯繘鐞嗚В鍨?",
            "pace": int(profile.pace or 50),
            "goal": profile.goal or "鎺屾彙鏍稿績鏁版嵁缁撴瀯涓庣畻娉?",
        },
        "updatedAt": isoformat_z(profile.updated_at),
    }


def _level_for_score(score: int) -> str:
    if score >= 85:
        return "鏄庤鲸澧?"
    if score >= 70:
        return "鑷寸煡澧?"
    if score >= 60:
        return "鏍肩墿澧?"
    return "鍚€濆"


def _status_for_mastery(value: int) -> str:
    if value < 60:
        return "weak"
    if value > 80:
        return "strong"
    return "ok"


@router.get("/profile/summary")
async def get_profile_summary(user_id: str = "guest_user", db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    if not profile:
        profile = StudentProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    score = int(profile.knowledge or 50)
    return api_response({
        "userId": profile.user_id,
        "knowledgeScore": score,
        "paceScore": int(profile.pace or 50),
        "cognitiveStyle": profile.cognitive or "娓愯繘鐞嗚В鍨?",
        "goal": profile.goal or "鎺屾彙鏍稿績鏁版嵁缁撴瀯涓庣畻娉?",
        "level": _level_for_score(score),
        "updatedAt": isoformat_z(profile.updated_at),
    })


@router.get("/profile/trends")
async def get_profile_trends(
    user_id: str = "guest_user",
    range_value: str = Query("7d", alias="range"),
    db: Session = Depends(get_db),
):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    knowledge = int(getattr(profile, "knowledge", 50) or 50)
    pace = int(getattr(profile, "pace", 50) or 50)
    days = 30 if range_value == "30d" else 7
    today = date(2026, 7, 8)
    return api_response({
        "knowledge": [
            {"date": (today - timedelta(days=days - 1 - i)).isoformat(), "value": max(0, min(100, knowledge - (days - 1 - i)))}
            for i in range(days)
        ],
        "pace": [
            {"date": (today - timedelta(days=days - 1 - i)).isoformat(), "value": max(0, min(100, pace - (days - 1 - i)))}
            for i in range(days)
        ],
    })


@router.get("/profile/knowledge-map")
async def get_profile_knowledge_map(
    user_id: str = "guest_user",
    rootId: str = "root",
    depth: int = 3,
    db: Session = Depends(get_db),
):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    mastery = int(getattr(profile, "knowledge", 72) or 72)
    tree_mastery = max(30, mastery - 27)
    graph_mastery = min(95, mastery + 13)
    return api_response({
        "id": rootId or "root",
        "name": "鏁版嵁缁撴瀯",
        "mastery": mastery,
        "status": _status_for_mastery(mastery),
        "children": [
            {
                "id": "ds_tree",
                "name": "鏍戜笌浜屽弶鏍?",
                "parentId": rootId or "root",
                "mastery": tree_mastery,
                "status": _status_for_mastery(tree_mastery),
                "relatedMistakeCount": 3,
                "recommendedActions": [
                    {"type": "quiz", "label": "鍋氫笓椤规祴璇?"},
                    {"type": "ask_ai", "label": "闂?AI 瀵煎笀"},
                ],
                "children": [] if depth <= 1 else [{
                    "id": "ds_btree_traverse",
                    "name": "浜屽弶鏍戦亶鍘?",
                    "parentId": "ds_tree",
                    "mastery": max(20, tree_mastery - 7),
                    "status": "weak",
                    "relatedMistakeCount": 2,
                    "recommendedActions": [],
                }],
            },
            {
                "id": "ds_graph",
                "name": "鍥捐",
                "parentId": rootId or "root",
                "mastery": graph_mastery,
                "status": _status_for_mastery(graph_mastery),
                "relatedMistakeCount": 0,
                "recommendedActions": [],
                "children": [],
            },
        ],
    })


@router.get("/profile/{user_id}")
async def get_profile(
    user_id: str,
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
    db: Session = Depends(get_db),
):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    if not profile:
        # 创建默认值
        profile = StudentProfile(
            user_id=user_id,
            knowledge=50,
            cognitive="渐进理解型",
            pace=50,
            error_pattern="易错点：数组越界，指针空悬",
            goal="掌握核心数据结构与算法",
            background="电子信息与计算机类"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    if is_miniprogram_client(x_gezhi_client):
        account = db.query(UserAccount).filter(UserAccount.username == user_id).first()
        return api_response(_profile_payload(profile, account))
    # 无 X-Gezhi-Client 头时（小程序云函数走此分支）
    # 返回与指导书 D.2 一致的扁平结构：name/class_name/avatar_url + knowledge/pace 在顶层
    account = db.query(UserAccount).filter(UserAccount.username == user_id).first()
    return {
        "user_id": profile.user_id,
        "name": (account.real_name if account else "") or profile.user_id,
        "class_name": (account.class_name if account else "") or "",
        "avatar_url": f"/static/avatars/{account.avatar_path}" if account and account.avatar_path else "",
        "knowledge": int(profile.knowledge or 50),
        "pace": int(profile.pace or 50),
        "cognitive": profile.cognitive or "",
        "goal": profile.goal or "",
        "background": profile.background or "",
        "error_pattern": profile.error_pattern or "",
    }

@router.post("/profile/update")
async def update_profile(data: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == data.user_id).first()
    if not profile:
        profile = StudentProfile(user_id=data.user_id)
        db.add(profile)
        
    if data.knowledge is not None:
        profile.knowledge = data.knowledge
    if data.cognitive is not None:
        profile.cognitive = data.cognitive
    if data.pace is not None:
        profile.pace = data.pace
    if data.error_pattern is not None:
        profile.error_pattern = data.error_pattern
    if data.goal is not None:
        profile.goal = data.goal
    if data.background is not None:
        profile.background = data.background
        
    db.commit()
    db.refresh(profile)
    return {"status": "success", "profile": profile}

@router.post("/profile/record_test")
async def record_test(data: TestResultRecord, db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == data.user_id).first()
    if not profile:
        profile = StudentProfile(
            user_id=data.user_id,
            knowledge=50,
            cognitive="渐进理解型",
            pace=50,
            error_pattern="易错点：数组越界，指针空悬",
            goal="掌握核心数据结构与算法",
            background="电子信息与计算机类"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
    # 根据做题结果动态计算画像变化
    # 比如：通过题目，增加 knowledge
    # 失败题目，降低 knowledge，并把错误信息记录到 error_pattern
    diff_factor = 2 if data.difficulty == "Easy" else (4 if data.difficulty == "Medium" else 6)
    
    if data.status == "passed":
        profile.knowledge = min(100, profile.knowledge + diff_factor)
        profile.pace = min(100, profile.pace + 2)
    else:
        profile.knowledge = max(10, profile.knowledge - int(diff_factor / 2))
        profile.pace = max(10, profile.pace - 1)
        
        # 记录特定错误类型到偏好中
        error_brief = f"在题 {data.problem_id} 中遇到错误"
        if data.error_msg:
            # 缩短并精简错误信息
            clean_err = data.error_msg.split('\n')[0]
            if len(clean_err) > 80:
                clean_err = clean_err[:80] + "..."
            error_brief += f": {clean_err}"
        
        # 拼接或覆盖原有错误
        current_pattern = profile.error_pattern or ""
        if error_brief not in current_pattern:
            if current_pattern:
                profile.error_pattern = f"易错：{data.category} -> {error_brief} | {current_pattern}"[:500]
            else:
                profile.error_pattern = f"易错：{data.category} -> {error_brief}"
                
    db.commit()
    db.refresh(profile)
    return {"status": "success", "profile": profile}
