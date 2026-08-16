import json
import random
import threading
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain_record import DomainRecord
from app.models.ranked_question import RankedQuestion
from app.repositories.json_store import JsonStore, load_payload
from app.services.model_registry import build_chat_model, has_model
from app.services.learning_diagnosis.activity_listener import publish_learning_activity_safely

router = APIRouter()
DEFAULT_RANKED_COACH_MODEL = "qwen3.7-plus"
_RANKED_SETTLEMENT_LOCK_STRIPES = 64
_RANKED_SETTLEMENT_LOCKS = tuple(threading.Lock() for _ in range(_RANKED_SETTLEMENT_LOCK_STRIPES))


class MatchStartPayload(BaseModel):
    userId: str
    mode: Optional[str] = "ranked"


class RankedMistakePatchPayload(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None


class RankedCoachPayload(BaseModel):
    userId: str
    agentId: Optional[str] = "agent_ranked_coach"
    agentName: Optional[str] = "排位赛AI教练"
    agentModel: Optional[str] = DEFAULT_RANKED_COACH_MODEL
    agentPrompt: Optional[str] = ""
    question: str
    context: Optional[dict] = None


class RankedMistakeAiPayload(BaseModel):
    userId: str
    agentId: Optional[str] = "agent_ranked_coach"
    agentName: Optional[str] = "排位赛AI教练"
    agentModel: Optional[str] = DEFAULT_RANKED_COACH_MODEL
    agentPrompt: Optional[str] = ""
    context: Optional[dict] = None


class RankedTestResultPayload(BaseModel):
    label: Optional[str] = ""
    input: Optional[Any] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    status: Optional[str] = ""
    error: Optional[str] = ""


class RankedMatchSubmitPayload(BaseModel):
    userId: str
    result: Optional[str] = "loss"
    code: Optional[str] = ""
    durationSeconds: Optional[int] = 0
    passedCount: Optional[int] = 0
    totalCount: Optional[int] = 0
    testResults: Optional[list[dict[str, Any]]] = None
    cheatReason: Optional[str] = ""


def _now_text():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _settlement_lock_for(match_id: str) -> threading.Lock:
    return _RANKED_SETTLEMENT_LOCKS[hash(match_id) % len(_RANKED_SETTLEMENT_LOCKS)]


def _get_domain_record(
    db: Session,
    module: str,
    record_type: str,
    record_key: str,
    owner_id: str | None = None,
) -> DomainRecord | None:
    query = db.query(DomainRecord).filter(
        DomainRecord.module == module,
        DomainRecord.record_type == record_type,
        DomainRecord.record_key == record_key,
    )
    if owner_id is not None:
        query = query.filter(DomainRecord.owner_id == owner_id)
    return query.order_by(DomainRecord.id.desc()).first()


def _get_ranked_match_record_for_update(db: Session, match_id: str, user_id: str) -> DomainRecord | None:
    return (
        db.query(DomainRecord)
        .filter(
            DomainRecord.module == "ranked",
            DomainRecord.record_type == "match",
            DomainRecord.record_key == match_id,
            DomainRecord.owner_id == user_id,
        )
        .order_by(DomainRecord.id.desc())
        .with_for_update()
        .first()
    )


def _get_ranked_payload_no_commit(
    db: Session,
    record_type: str,
    record_key: str,
    owner_id: str | None = None,
) -> dict[str, Any] | None:
    return load_payload(_get_domain_record(db, "ranked", record_type, record_key, owner_id=owner_id))


def _upsert_ranked_payload_no_commit(
    db: Session,
    record_type: str,
    record_key: str,
    payload: dict[str, Any],
    *,
    owner_id: str = "",
    role: str = "",
    status: str = "",
    existing_record: DomainRecord | None = None,
) -> dict[str, Any]:
    record = existing_record or _get_domain_record(db, "ranked", record_type, record_key, owner_id=owner_id)
    stored_payload = dict(payload or {})
    stored_payload.setdefault("id", record_key)
    if not record:
        record = DomainRecord(
            module="ranked",
            record_type=record_type,
            record_key=record_key,
            owner_id=owner_id or "",
            role=role or "",
        )
        db.add(record)
    record.status = status or stored_payload.get("status") or record.status or ""
    record.payload = json.dumps(stored_payload, ensure_ascii=False, default=str)
    return load_payload(record) or stored_payload


def _format_duration(seconds: int | None) -> str:
    total = max(0, int(seconds or 0))
    minutes = total // 60
    remain = total % 60
    return f"{minutes}分{remain}秒"


def _tier_for_score(score: int) -> dict[str, str | int]:
    tiers = [
        (5200, "king", "王者段位", 100),
        (3800, "diamond", "钻石段位", 100),
        (2600, "platinum", "铂金段位", 100),
        (1600, "gold", "黄金段位", min(100, max(0, round((score - 1600) / 1000 * 100)))),
        (800, "silver", "白银段位", min(100, max(0, round((score - 800) / 800 * 100)))),
        (0, "bronze", "青铜段位", min(100, max(0, round(score / 800 * 100)))),
    ]
    for threshold, code, label, progress in tiers:
        if score >= threshold:
            return {"tierCode": code, "tier": label, "progress": progress}
    return {"tierCode": "bronze", "tier": "青铜段位", "progress": 0}


def _build_ranked_dashboard_data(user_id: str, db: Session) -> dict:
    _ensure_ranked_seed(db, user_id)
    store = JsonStore(db)
    return {
        "player": store.get_payload("ranked", "profile", user_id),
        "leaderboard": (store.get_payload("ranked", "leaderboard", "default") or {}).get("items", []),
        "dailyChallenge": store.get_payload("ranked", "daily_challenge", user_id),
        "rules": (store.get_payload("ranked", "rules", "default") or {}).get("items", []),
        "tierLadder": (store.get_payload("ranked", "tier_ladder", "default") or {}).get("items", []),
    }


def _failed_case_labels(test_results: list[dict[str, Any]]) -> list[str]:
    labels = []
    for index, item in enumerate(test_results, start=1):
        if item.get("status") != "passed":
            labels.append(str(item.get("label") or f"case {index}"))
    return labels


def _resolve_ranked_model(model_id: Optional[str]) -> str:
    if model_id and has_model(model_id, category="text"):
        return model_id
    return DEFAULT_RANKED_COACH_MODEL


def _message_content(message) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def _parse_ai_analysis(content: str) -> dict:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return {
                "diagnosis": parsed.get("diagnosis") or parsed.get("summary") or content,
                "concept": parsed.get("concept") or parsed.get("knowledge") or "",
                "practice": parsed.get("practice") or parsed.get("suggestion") or "",
                "path": parsed.get("path") if isinstance(parsed.get("path"), list) else [],
            }
    except Exception:
        pass
    return {
        "diagnosis": content,
        "concept": "",
        "practice": "请根据本题错因完成 3 道同知识点递进训练题。",
        "path": ["复盘错因", "补齐知识点", "限时训练", "排位复测"],
    }


def _build_coach_prompt(*, agent_prompt: str, question: str, context: dict) -> str:
    return f"""你是竞技排位赛页面中的排位 AI 教练。

系统指令：
{agent_prompt or "基于排位数据给出具体、可执行的提分建议。"}

学生问题：
{question}

排位上下文 JSON：
{json.dumps(context or {}, ensure_ascii=False, indent=2)}

请用中文回答，聚焦：失误定位、知识点补强、训练节奏、赛季冲分策略。"""


def _build_mistake_prompt(*, agent_prompt: str, mistake: dict, context: dict) -> str:
    return f"""你是竞技排位赛页面中的排位 AI 教练，需要分析排位错题。

系统指令：
{agent_prompt or "诊断排位错题并给出可执行训练路径。"}

错题信息 JSON：
{json.dumps(mistake, ensure_ascii=False, indent=2)}

额外上下文 JSON：
{json.dumps(context or {}, ensure_ascii=False, indent=2)}

请输出 JSON，字段为 diagnosis、concept、practice、path。path 是 3 到 5 个短步骤。"""


def _seed_profile(user_id: str):
    return {
        "studentId": user_id,
        "name": "林屿安",
        "className": "计算机学院 · 软工2班",
        "tier": "黄金段位",
        "tierCode": "gold",
        "score": 1980,
        "nextTier": "铂金段位",
        "nextTierNeed": 620,
        "streak": 5,
        "progress": 68,
        "badge": "./assets/ranked/badge-gold.png",
    }


def _seed_leaderboard(user_id: str):
    return [
        {"rank": 1, "name": "苏晚晴", "className": "计算机学院", "tier": "platinum", "streak": 12, "score": 4120},
        {"rank": 2, "name": "林屿安", "className": "计算机学院", "tier": "gold", "streak": 5, "score": 1980, "studentId": user_id, "isCurrent": True},
        {"rank": 3, "name": "沈砚辞", "className": "计算机学院", "tier": "gold", "streak": 3, "score": 1840},
        {"rank": 4, "name": "周叙白", "className": "计算机学院", "tier": "silver", "streak": 0, "score": 1320},
        {"rank": 5, "name": "许清和", "className": "计算机学院", "tier": "silver", "streak": 2, "score": 990},
        {"rank": 6, "name": "温知予", "className": "计算机学院", "tier": "gold", "streak": 1, "score": 540},
    ]


def _seed_daily_challenge(user_id: str):
    return {
        "id": f"daily-{user_id}",
        "studentId": user_id,
        "title": "完成 2 道图搜索 / Cache 模拟题目",
        "tag": "课程综合 · 图搜索与组成原理",
        "reward": 180,
        "progress": 1,
        "total": 2,
        "date": "2026-07-06",
    }


def _seed_rules():
    return [
        {"title": "匹配对决", "desc": "系统按你的段位匹配同水平题目与对手，胜负即时结算。", "icon": "ph-swords"},
        {"title": "积分收益", "desc": "通过全部测试用例判定胜利，按题目难度获得基础荣誉积分。", "icon": "ph-coins"},
        {"title": "连胜加成", "desc": "连续期间每胜一场额外加成，最高叠加 10 连胜（+50%）。", "icon": "ph-fire"},
        {"title": "失利扣分", "desc": "未通过全部用例视为失利，按题目扣除积分并中断连胜。", "icon": "ph-minus-circle"},
        {"title": "每日挑战", "desc": "每日刷新特定知识点任务，完成后领取额外荣誉积分。", "icon": "ph-target"},
        {"title": "赛季结算", "desc": "一个学期为一个赛季，赛季末按最终段位发放勋章与奖励。", "icon": "ph-calendar-check"},
    ]


def _seed_tier_ladder():
    return [
        {"name": "王者", "range": "荣誉积分 5200 分以上", "level": "LV.6", "color": "orange", "isPeak": True},
        {"name": "钻石", "range": "荣誉积分 3800 ~ 5199 分", "level": "LV.5", "color": "blue"},
        {"name": "铂金", "range": "荣誉积分 2600 ~ 3799 分", "level": "LV.4", "color": "cyan"},
        {"name": "黄金", "range": "荣誉积分 1600 ~ 2599 分", "level": "LV.3", "color": "gold"},
        {"name": "白银", "range": "荣誉积分 800 ~ 1599 分", "level": "LV.2", "color": "silver"},
        {"name": "青铜", "range": "荣誉积分 0 ~ 799 分", "level": "LV.1", "color": "bronze"},
    ]


def _seed_mistakes(user_id: str):
    return [
        {
            "id": f"ranked-mistake-{user_id}-1",
            "studentId": user_id,
            "title": "岛屿数量",
            "type": "算法题",
            "knowledge": "并查集 / DFS",
            "wrongCount": 2,
            "lastWrongAt": "2026.7.4",
            "status": "review",
            "risk": "遍历越界",
            "errorPhenomenon": "DFS 未做边界判断，网格四邻访问时数组越界导致部分用例失败。",
            "note": "",
        },
        {
            "id": f"ranked-mistake-{user_id}-2",
            "studentId": user_id,
            "title": "最短路径 Dijkstra",
            "type": "算法题",
            "knowledge": "最短路 / 堆",
            "wrongCount": 3,
            "lastWrongAt": "2026.7.2",
            "status": "review",
            "risk": "超时",
            "errorPhenomenon": "使用邻接矩阵朴素实现，未用优先队列优化，大数据用例 TLE。",
            "note": "复习堆优化 Dijkstra 的模板。",
        },
    ]


def _seed_seasons(user_id: str):
    return [
        {
            "id": f"season-2026-spring-{user_id}",
            "studentId": user_id,
            "title": "2026 春季学期",
            "status": "进行中",
            "dateRange": "2026-02-24 ~ 2026-07-12",
            "score": 1980,
            "tier": "黄金段位",
            "progress": 96,
            "winRate": "73%",
            "highestStreak": 5,
            "peakTier": "黄金",
            "schoolRank": "#6",
        },
        {
            "id": f"season-2025-autumn-{user_id}",
            "studentId": user_id,
            "title": "2025 秋季学期",
            "status": "已结束",
            "dateRange": "2025-09-01 ~ 2026-01-18",
            "score": 1460,
            "tier": "白银段位",
            "progress": 100,
            "winRate": "60%",
            "highestStreak": 7,
            "peakTier": "黄金",
            "schoolRank": "#21",
        },
    ]


def _ensure_ranked_seed(db: Session, user_id: str):
    store = JsonStore(db)
    if not store.get_payload("ranked", "profile", user_id):
        store.upsert("ranked", "profile", user_id, _seed_profile(user_id), owner_id=user_id, status="active")
    if not store.get_payload("ranked", "leaderboard", "default"):
        store.upsert("ranked", "leaderboard", "default", {"items": _seed_leaderboard(user_id)}, owner_id="", status="active")
    if not store.get_payload("ranked", "daily_challenge", user_id):
        store.upsert("ranked", "daily_challenge", user_id, _seed_daily_challenge(user_id), owner_id=user_id, status="active")
    if not store.get_payload("ranked", "rules", "default"):
        store.upsert("ranked", "rules", "default", {"items": _seed_rules()}, owner_id="", status="active")
    if not store.get_payload("ranked", "tier_ladder", "default"):
        store.upsert("ranked", "tier_ladder", "default", {"items": _seed_tier_ladder()}, owner_id="", status="active")
    if not store.list_payloads("ranked", record_type="mistake", owner_id=user_id):
        for mistake in _seed_mistakes(user_id):
            store.upsert("ranked", "mistake", mistake["id"], mistake, owner_id=user_id, status="active")
    if not store.list_payloads("ranked", record_type="season", owner_id=user_id):
        for season in _seed_seasons(user_id):
            store.upsert("ranked", "season", season["id"], season, owner_id=user_id, status="active")


@router.get("/ranked/student/{user_id}/dashboard")
async def get_ranked_dashboard(user_id: str, db: Session = Depends(get_db)):
    return {"status": "success", "data": _build_ranked_dashboard_data(user_id, db)}


@router.get("/ranked/student/{user_id}/history")
async def get_match_history(user_id: str, db: Session = Depends(get_db)):
    _ensure_ranked_seed(db, user_id)
    matches = JsonStore(db).list_payloads("ranked", record_type="match", owner_id=user_id)
    return {"status": "success", "data": matches}


@router.get("/ranked/student/{user_id}/mistakes")
async def get_ranked_mistakes(user_id: str, db: Session = Depends(get_db)):
    _ensure_ranked_seed(db, user_id)
    mistakes = JsonStore(db).list_payloads("ranked", record_type="mistake", owner_id=user_id, status="active")
    return {"status": "success", "data": mistakes}


@router.get("/ranked/student/{user_id}/seasons")
async def get_ranked_seasons(user_id: str, db: Session = Depends(get_db)):
    _ensure_ranked_seed(db, user_id)
    seasons = JsonStore(db).list_payloads("ranked", record_type="season", owner_id=user_id, status="active")
    return {"status": "success", "data": seasons}


@router.get("/ranked/questions")
async def list_ranked_questions(
    difficulty: Optional[str] = None,
    min_tier: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(RankedQuestion)
    if difficulty:
        query = query.filter(RankedQuestion.difficulty == difficulty)
    if min_tier:
        query = query.filter(RankedQuestion.min_tier == min_tier)
    questions = query.all()
    
    # 转换为 dict 并解析 JSON 字段
    result = []
    for q in questions:
        q_dict = {
            "id": q.id,
            "questionId": q.question_id,
            "title": q.title,
            "difficulty": q.difficulty,
            "minTier": q.min_tier,
            "category": q.category,
            "scoreReward": q.score_reward,
            "scorePenalty": q.score_penalty,
            "timeLimitSec": q.time_limit_sec,
            "description": q.description,
            "inputFormat": q.input_format,
            "outputFormat": q.output_format,
            "constraints": q.constraints,
            "hint": q.hint,
        }
        try:
            q_dict["knowledgeTags"] = json.loads(q.knowledge_tags)
        except Exception:
            q_dict["knowledgeTags"] = []
        try:
            q_dict["examples"] = json.loads(q.examples)
        except Exception:
            q_dict["examples"] = []
        result.append(q_dict)
        
    return {"status": "success", "data": result}


@router.get("/ranked/questions/{question_id}")
async def get_ranked_question(question_id: str, db: Session = Depends(get_db)):
    q = db.query(RankedQuestion).filter(RankedQuestion.question_id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
        
    q_dict = {
        "id": q.id,
        "questionId": q.question_id,
        "title": q.title,
        "difficulty": q.difficulty,
        "minTier": q.min_tier,
        "category": q.category,
        "scoreReward": q.score_reward,
        "scorePenalty": q.score_penalty,
        "timeLimitSec": q.time_limit_sec,
        "description": q.description,
        "inputFormat": q.input_format,
        "outputFormat": q.output_format,
        "constraints": q.constraints,
        "hint": q.hint,
    }
    try:
        q_dict["knowledgeTags"] = json.loads(q.knowledge_tags)
    except Exception:
        q_dict["knowledgeTags"] = []
    try:
        q_dict["examples"] = json.loads(q.examples)
    except Exception:
        q_dict["examples"] = []
        
    return {"status": "success", "data": q_dict}


@router.post("/ranked/matches/start")
async def start_ranked_match(payload: MatchStartPayload, db: Session = Depends(get_db)):
    _ensure_ranked_seed(db, payload.userId)
    store = JsonStore(db)
    
    # 1. 获取用户段位
    profile = store.get_payload("ranked", "profile", payload.userId)
    tier_code = "gold"  # 默认黄金
    if profile and "tierCode" in profile:
        tier_code = profile["tierCode"].lower()
        
    # 2. 映射段位到难度
    # 简单(easy): bronze/silver; 中等(medium): gold/platinum; 困难(hard): diamond/king (包括其他比如master之类)
    if tier_code in ["bronze", "silver"]:
        target_diff = "easy"
    elif tier_code in ["gold", "platinum"]:
        target_diff = "medium"
    else:
        target_diff = "hard"
        
    # 3. 从数据库中筛选符合难度的题目
    candidates = db.query(RankedQuestion).filter(RankedQuestion.difficulty == target_diff).all()
    if not candidates:
        # 如果当前难度无题目，获取所有题目作为候选
        candidates = db.query(RankedQuestion).all()
        
    # 4. 随机匹配一题
    if candidates:
        selected_q = random.choice(candidates)
        q_info = {
            "questionId": selected_q.question_id,
            "title": selected_q.title,
            "difficulty": selected_q.difficulty,
            "minTier": selected_q.min_tier,
            "category": selected_q.category,
            "description": selected_q.description,
            "inputFormat": selected_q.input_format,
            "outputFormat": selected_q.output_format,
            "constraints": selected_q.constraints,
            "hint": selected_q.hint,
            "scoreReward": selected_q.score_reward,
            "scorePenalty": selected_q.score_penalty,
            "timeLimitSec": selected_q.time_limit_sec,
        }
        try:
            q_info["knowledgeTags"] = json.loads(selected_q.knowledge_tags)
        except Exception:
            q_info["knowledgeTags"] = []
        try:
            q_info["examples"] = json.loads(selected_q.examples)
        except Exception:
            q_info["examples"] = []
    else:
        # 回退默认值，以防数据库完全为空
        q_info = {
            "questionId": "q_fallback",
            "title": "程序逻辑测试题",
            "difficulty": target_diff,
            "minTier": "bronze",
            "category": "通用编程",
            "description": "请实现一个算法，计算两个整数的和。",
            "inputFormat": "输入两个整数 A 和 B。",
            "outputFormat": "输出 A + B 的结果。",
            "constraints": "-10^5 <= A, B <= 10^5",
            "hint": "直接相加即可。",
            "scoreReward": 50,
            "scorePenalty": 20,
            "timeLimitSec": 600,
            "knowledgeTags": ["基础输入输出"],
            "examples": [{"input": "1 2", "output": "3"}]
        }
        
    match_id = f"ranked-match-{uuid4().hex[:10]}"
    match = {
        "id": match_id,
        "studentId": payload.userId,
        "title": q_info["title"],
        "type": "编程题",
        "result": "matched",
        "scoreDelta": 0,
        "duration": "00分00秒",
        "createdAt": _now_text(),
        "status": "pending",
        "questionId": q_info["questionId"],
        "question": q_info
    }
    
    store.upsert("ranked", "match", match_id, match, owner_id=payload.userId, status="active")
    return {"status": "success", "data": match}


def _settlement_result(payload: RankedMatchSubmitPayload) -> str:
    if payload.result == "cheat_lose":
        return "cheat_lose"
    total = int(payload.totalCount or 0)
    passed = int(payload.passedCount or 0)
    if total > 0 and passed >= total:
        return "win"
    return "loss"


def _score_delta(result: str, question: dict[str, Any]) -> int:
    reward = int(question.get("scoreReward") or 231)
    penalty = int(question.get("scorePenalty") or 100)
    if result == "win":
        return reward
    if result == "cheat_lose":
        return -max(100, penalty)
    return -penalty


def _update_ranked_profile(db: Session, user_id: str, result: str, delta: int) -> dict:
    profile = _get_ranked_payload_no_commit(db, "profile", user_id) or _seed_profile(user_id)
    score = max(0, int(profile.get("score") or 0) + int(delta))
    profile["score"] = score
    profile["streak"] = int(profile.get("streak") or 0) + 1 if result == "win" else 0
    profile.update(_tier_for_score(score))
    profile["updatedAt"] = _now_iso()
    return _upsert_ranked_payload_no_commit(db, "profile", user_id, profile, owner_id=user_id, status="active")


def _build_error_phenomenon(
    result: str,
    payload: RankedMatchSubmitPayload,
    test_results: list[dict[str, Any]],
) -> str:
    if result == "cheat_lose":
        return f"security violation: {payload.cheatReason or 'no reason provided'}"
    failed = _failed_case_labels(test_results)
    failed_text = ", ".join(failed) if failed else "no failed cases recorded"
    return (
        f"public cases passed {int(payload.passedCount or 0)}/{int(payload.totalCount or 0)}; "
        f"failed cases: {failed_text}"
    )


def _upsert_ranked_mistake(
    db: Session,
    *,
    user_id: str,
    match: dict[str, Any],
    result: str,
    payload: RankedMatchSubmitPayload,
    test_results: list[dict[str, Any]],
) -> dict:
    question = match.get("question") or {}
    question_id = str(match.get("questionId") or question.get("questionId") or "unknown")
    mistake_id = f"ranked-mistake:{user_id}:{question_id}"
    existing = _get_ranked_payload_no_commit(db, "mistake", mistake_id)
    now = _now_iso()
    wrong_count = int((existing or {}).get("wrongCount") or 0) + 1
    mistake = {
        **(existing or {}),
        "id": mistake_id,
        "studentId": user_id,
        "questionId": question_id,
        "matchId": match.get("id"),
        "title": match.get("title") or question.get("title") or "unknown ranked question",
        "type": match.get("type") or "programming question",
        "knowledge": " / ".join(question.get("knowledgeTags") or []) or question.get("category") or "",
        "knowledgeTags": question.get("knowledgeTags") or [],
        "wrongCount": wrong_count,
        "lastWrongAt": now,
        "status": "review",
        "risk": "security_violation" if result == "cheat_lose" else "not_all_tests_passed",
        "errorPhenomenon": _build_error_phenomenon(result, payload, test_results),
        "studentCode": payload.code or "",
        "testResults": test_results,
        "source": {"type": "ranked_match", "matchId": match.get("id"), "questionId": question_id},
        "mastered": False,
        "createdAt": (existing or {}).get("createdAt") or now,
        "updatedAt": now,
    }
    mistake.pop("deletedAt", None)
    mistake.pop("deletedBy", None)
    return _upsert_ranked_payload_no_commit(db, "mistake", mistake_id, mistake, owner_id=user_id, status="active")


@router.post("/ranked/matches/{match_id}/submit")
async def submit_ranked_match(
    match_id: str,
    payload: RankedMatchSubmitPayload,
    db: Session = Depends(get_db),
):
    with _settlement_lock_for(match_id):
        match_record = _get_ranked_match_record_for_update(db, match_id, payload.userId)
        match = load_payload(match_record)
        if not match:
            db.rollback()
            raise HTTPException(status_code=404, detail="ranked match not found")
        if match.get("studentId") != payload.userId:
            db.rollback()
            raise HTTPException(status_code=403, detail="forbidden: cannot submit another student's match")
        if match.get("status") == "settled":
            profile = _get_ranked_payload_no_commit(db, "profile", payload.userId) or _seed_profile(payload.userId)
            mistake = None
            if match.get("result") in ("loss", "cheat_lose"):
                question = match.get("question") or {}
                question_id = str(match.get("questionId") or question.get("questionId") or "unknown")
                mistake = _get_ranked_payload_no_commit(db, "mistake", f"ranked-mistake:{payload.userId}:{question_id}")
            db.rollback()
            return {"status": "success", "data": {"match": match, "profile": profile, "mistake": mistake}}

        try:
            test_results = list(payload.testResults or [])
            result = _settlement_result(payload)
            question = match.get("question") or {}
            delta = _score_delta(result, question)
            submitted_at = _now_iso()
            updated_match = {
                **match,
                "status": "settled",
                "result": result,
                "scoreDelta": delta,
                "duration": _format_duration(payload.durationSeconds),
                "durationSeconds": int(payload.durationSeconds or 0),
                "submittedAt": submitted_at,
                "code": payload.code or "",
                "testResults": test_results,
                "passedCount": int(payload.passedCount or 0),
                "totalCount": int(payload.totalCount or 0),
                "cheatReason": payload.cheatReason or "",
                "updatedAt": submitted_at,
            }
            stored_match = _upsert_ranked_payload_no_commit(
                db,
                "match",
                match_id,
                updated_match,
                owner_id=payload.userId,
                status="active",
                existing_record=match_record,
            )
            profile = _update_ranked_profile(db, payload.userId, result, delta)
            mistake = None
            if result in ("loss", "cheat_lose"):
                mistake = _upsert_ranked_mistake(
                    db,
                    user_id=payload.userId,
                    match=stored_match,
                    result=result,
                    payload=payload,
                    test_results=test_results,
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
        try:
            question_id = str(stored_match.get("questionId") or (stored_match.get("question") or {}).get("questionId") or "")
            await publish_learning_activity_safely(db, {
                "student_id": payload.userId, "source_module": "ranked", "content_type": "RANKED_QUESTION",
                "content_id": question_id, "attempt_id": match_id,
                "result_payload": {"result": stored_match.get("result"), "passed": stored_match.get("result") == "win", "passed_count": int(payload.passedCount or 0), "total_count": int(payload.totalCount or 0)},
                "status": "COMPLETED", "occurred_at": stored_match.get("submittedAt") or _now_iso(),
            })
        except Exception:
            pass
        return {"status": "success", "data": {"match": stored_match, "profile": profile, "mistake": mistake}}


@router.patch("/ranked/mistakes/{mistake_id}")
async def update_ranked_mistake(mistake_id: str, payload: RankedMistakePatchPayload, db: Session = Depends(get_db)):
    store = JsonStore(db)
    current = store.get_payload("ranked", "mistake", mistake_id) or {"id": mistake_id}
    patch = {key: value for key, value in payload.model_dump().items() if value is not None}
    updated = {**current, **patch, "updatedAt": _now_text()}
    store.upsert("ranked", "mistake", mistake_id, updated, owner_id=updated.get("studentId", ""), status="active")
    return {"status": "success", "data": updated}


@router.delete("/ranked/mistakes/{mistake_id}")
async def delete_ranked_mistake(mistake_id: str, userId: str, db: Session = Depends(get_db)):
    store = JsonStore(db)
    current = store.get_payload("ranked", "mistake", mistake_id, owner_id=userId)
    if not current:
        raise HTTPException(status_code=404, detail="ranked mistake not found")
    if current.get("studentId") != userId:
        raise HTTPException(status_code=403, detail="forbidden: cannot delete another student's mistake")
    now = _now_iso()
    updated = {**current, "status": "deleted", "deletedAt": now, "deletedBy": userId, "updatedAt": now}
    stored = store.upsert("ranked", "mistake", mistake_id, updated, owner_id=userId, status="deleted")
    return {"status": "success", "data": stored}


@router.post("/ranked/coach/ask")
async def ask_ranked_coach(payload: RankedCoachPayload, db: Session = Depends(get_db)):
    model_id = _resolve_ranked_model(payload.agentModel)
    dashboard = _build_ranked_dashboard_data(payload.userId, db)
    prompt = _build_coach_prompt(
        agent_prompt=payload.agentPrompt or "",
        question=payload.question,
        context={**dashboard, **(payload.context or {})},
    )
    try:
        message = build_chat_model(model_id, temperature=0.1).invoke(prompt)
        answer = _message_content(message)
    except Exception as exc:
        answer = f"排位 AI 教练暂时无法连接模型，先按当前数据建议：复盘最近错题，优先补强高频失误知识点。错误：{exc}"
    return {
        "status": "success",
        "data": {
            "answer": answer,
            "agentId": payload.agentId or "agent_ranked_coach",
            "agentName": payload.agentName or "排位赛AI教练",
            "model": model_id,
            "createdAt": _now_text(),
        },
    }


@router.post("/ranked/mistakes/{mistake_id}/ai-analysis")
async def analyze_ranked_mistake(
    mistake_id: str,
    payload: RankedMistakeAiPayload,
    db: Session = Depends(get_db),
):
    _ensure_ranked_seed(db, payload.userId)
    store = JsonStore(db)
    mistake = store.get_payload("ranked", "mistake", mistake_id)
    if not mistake:
        mistake = {"id": mistake_id, "studentId": payload.userId, "title": "未知排位错题"}
    model_id = _resolve_ranked_model(payload.agentModel)
    prompt = _build_mistake_prompt(
        agent_prompt=payload.agentPrompt or "",
        mistake=mistake,
        context=payload.context or {},
    )
    try:
        message = build_chat_model(model_id, temperature=0.1).invoke(prompt)
        analysis = _parse_ai_analysis(_message_content(message))
    except Exception as exc:
        analysis = {
            "diagnosis": f"排位 AI 教练暂时无法连接模型，先按错因进行模板复盘。错误：{exc}",
            "concept": mistake.get("knowledge", ""),
            "practice": "重做本题并完成 3 道同知识点题目。",
            "path": ["复盘错因", "重写模板", "限时训练", "排位复测"],
        }
    analysis.update(
        {
            "source": "ai",
            "agentId": payload.agentId or "agent_ranked_coach",
            "agentName": payload.agentName or "排位赛AI教练",
            "model": model_id,
            "createdAt": _now_text(),
        }
    )
    updated = {**mistake, "aiAnalysis": analysis, "updatedAt": _now_text()}
    store.upsert("ranked", "mistake", mistake_id, updated, owner_id=updated.get("studentId", payload.userId), status="active")
    return {"status": "success", "data": analysis}
