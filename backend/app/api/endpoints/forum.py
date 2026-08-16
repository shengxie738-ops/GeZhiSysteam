import re
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.miniprogram_response import api_response, is_miniprogram_client, page_items
from app.core.responses import ok
from app.repositories.json_store import JsonStore, make_record_key
from app.utils.datetime import utc_now_iso
from app.api.endpoints.auth import get_current_user

router = APIRouter()


def _normalize_avatar_url(url: str) -> str:
    """将 avatar URL 规范化为相对路径。
    去除 localhost / 127.0.0.1 等开发环境前缀，只保留 /static/... 路径部分。
    """
    if not url:
        return ""
    # 匹配 http(s)://localhost:port/... 或 http(s)://127.0.0.1:port/...
    match = re.match(r'^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(/.*)$', url)
    if match:
        return match.group(1)
    return url

def require_user(current_user = Depends(get_current_user)):
    # get_current_user returns auth_fail() (a JSONResponse) when unauthenticated,
    # or auth_ok(data=...) (a plain dict) when authenticated.
    if isinstance(current_user, JSONResponse) or (
        isinstance(current_user, dict) and current_user.get("success") is False
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if isinstance(current_user, dict):
        return current_user.get("data")
    raise HTTPException(status_code=401, detail="Unauthorized")


class FreePayload(BaseModel):
    class Config:
        extra = "allow"


def _category_label(category: str) -> str:
    return {
        "qna": "Course Q&A",
        "competition": "Competition",
        "experience": "Experience",
        "chat": "Chat",
    }.get(category, category or "Course Q&A")


def _is_teacher_reply(reply: dict) -> bool:
    """判断回复是否来自教师：author 含"教师"或"老师"关键词"""
    author = reply.get("author") or ""
    return "教师" in author or "老师" in author


def _is_post_answered_by_teacher(post: dict) -> bool:
    """判断帖子是否已被教师回复"""
    return any(_is_teacher_reply(r) for r in (post.get("replies") or []))


def _normalize_post_avatars(post: dict) -> dict:
    """规范化帖子及其回复中的 avatar URL。"""
    if post.get("avatar"):
        post["avatar"] = _normalize_avatar_url(post["avatar"])
    for reply in post.get("replies") or []:
        if reply.get("avatar"):
            reply["avatar"] = _normalize_avatar_url(reply["avatar"])
    return post


@router.get("/forum/posts")
async def get_posts(
    db: Session = Depends(get_db),
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
):
    posts = JsonStore(db).list_payloads("forum", "post")
    posts = [_normalize_post_avatars(p) for p in posts]
    if is_miniprogram_client(x_gezhi_client):
        return api_response(page_items(posts, limit=len(posts) or 20))
    return ok(posts)


@router.get("/forum/unanswered-qna")
async def get_unanswered_qna(limit: int = 5, db: Session = Depends(get_db)):
    """获取最新未被教师答疑的课程答疑帖子。
    筛选条件：category=qna 且 replies 中无教师回复（author 含"教师"或"老师"）。
    按 createdAt 降序，取前 limit 条（上限 20）。
    """
    limit = max(1, min(limit, 20))
    posts = JsonStore(db).list_payloads("forum", "post")
    unanswered = [
        post for post in posts
        if post.get("category") == "qna" and not _is_post_answered_by_teacher(post)
    ]
    unanswered.sort(key=lambda p: p.get("createdAt", ""), reverse=True)
    result = []
    for post in unanswered[:limit]:
        result.append({
            "id": post.get("id", ""),
            "title": post.get("title", ""),
            "content": post.get("content", ""),
            "author": post.get("author", "anonymous"),
            "avatar": _normalize_avatar_url(post.get("avatar", "")),
            "createdAt": post.get("createdAt", ""),
            "tags": post.get("tags", []),
            "views": post.get("views", 0),
            "likes": post.get("likes", 0),
            "repliesCount": len(post.get("replies") or []),
        })
    return ok(result)


@router.post("/forum/posts")
async def create_post(payload: FreePayload, db: Session = Depends(get_db), current_user=Depends(require_user)):
    data = payload.model_dump()
    post_id = str(data.get("id") or make_record_key("post"))
    category = data.get("category") or "qna"
    # Prevent payload overwrite by overriding user data with our enforced defaults
    post = {**data}
    post.update({
        "id": post_id,
        "title": data.get("title") or "Untitled",
        "content": data.get("content") or "",
        "author": data.get("author") or "anonymous",
        "avatar": _normalize_avatar_url(data.get("avatar") or ""),
        "category": category,
        "categoryLabel": data.get("categoryLabel") or _category_label(category),
        "tags": data.get("tags") or [],
        "likes": 0,
        "isLiked": False,
        "views": 1,
        "createdAt": utc_now_iso(),
        "replies": [],
    })
    return ok(JsonStore(db).upsert("forum", "post", post_id, post))


@router.post("/forum/posts/{post_id}/replies")
async def create_reply(
    post_id: str,
    payload: FreePayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
):
    store = JsonStore(db)
    post = store.get_payload("forum", "post", post_id) or {"id": post_id, "replies": []}
    data = payload.model_dump()
    reply_id = str(data.get("id") or make_record_key("reply"))
    reply = {**data}
    reply.update({
        "id": reply_id,
        "author": data.get("author") or "anonymous",
        "avatar": _normalize_avatar_url(data.get("avatar") or ""),
        "isAi": bool(data.get("isAi", False)),
        "content": data.get("content") or "",
        "createdAt": utc_now_iso(),
        "likes": 0,
    })
    replies = post.get("replies") or []
    replies.append(reply)
    post["replies"] = replies
    store.upsert("forum", "post", post_id, post)
    if reply.get("isAi"):
        log_id = make_record_key("log")
        store.upsert(
            "forum",
            "ai_reply_log",
            log_id,
            {
                "id": log_id,
                "postId": post_id,
                "postTitle": post.get("title", ""),
                "replyId": reply_id,
                "agentName": reply.get("author") or "AI Tutor",
                "content": reply.get("content", ""),
                "time": utc_now_iso(),
                "status": "pending_audit",
            },
        )
    if is_miniprogram_client(x_gezhi_client):
        return api_response(reply)
    return ok(reply)


@router.delete("/forum/posts/{post_id}")
async def delete_post(post_id: str, db: Session = Depends(get_db), current_user=Depends(require_user)):
    return ok({"success": JsonStore(db).delete("forum", "post", post_id)})


@router.put("/forum/posts/{post_id}/pin")
async def set_post_pin(post_id: str, pinned: bool = False, db: Session = Depends(get_db), current_user=Depends(require_user)):
    store = JsonStore(db)
    post = store.get_payload("forum", "post", post_id)
    if post:
        post["isPinned"] = pinned
        store.upsert("forum", "post", post_id, post)
        if pinned:
            ann_id = f"ann-post-{post_id}"
            store.upsert("forum", "announcement", ann_id, {"id": ann_id, "title": f"[Pinned] {post.get('title', '')}", "date": "pinned"})
    return ok({"success": True})


@router.put("/forum/posts/{post_id}/like")
async def like_post(post_id: str, db: Session = Depends(get_db), current_user=Depends(require_user)):
    store = JsonStore(db)
    post = store.get_payload("forum", "post", post_id)
    if not post:
        return ok({"success": False, "message": "Post not found"})
    post["likes"] = post.get("likes", 0) + 1
    # Note: ideally we should track which user liked the post in a separate array/set to prevent duplicate likes,
    # but to maintain compatibility with the frontend structure without major DB redesign, we just increment.
    store.upsert("forum", "post", post_id, post)
    return ok(post)


@router.put("/forum/posts/{post_id}/replies/{reply_id}/like")
async def like_reply(post_id: str, reply_id: str, db: Session = Depends(get_db), current_user=Depends(require_user)):
    store = JsonStore(db)
    post = store.get_payload("forum", "post", post_id)
    if not post:
        return ok({"success": False, "message": "Post not found"})
    target_reply = None
    for reply in post.get("replies", []):
        if reply.get("id") == reply_id:
            reply["likes"] = reply.get("likes", 0) + 1
            target_reply = reply
            break
    if target_reply:
        store.upsert("forum", "post", post_id, post)
        return ok(target_reply)
    return ok({"success": False, "message": "Reply not found"})


@router.put("/forum/posts/{post_id}/view")
async def view_post(post_id: str, db: Session = Depends(get_db)):
    store = JsonStore(db)
    post = store.get_payload("forum", "post", post_id)
    if not post:
        return ok({"success": False})
    post["views"] = post.get("views", 0) + 1
    store.upsert("forum", "post", post_id, post)
    return ok(_normalize_post_avatars(post))


@router.get("/forum/announcements")
async def get_announcements(db: Session = Depends(get_db)):
    return ok(JsonStore(db).list_payloads("forum", "announcement"))


@router.post("/forum/announcements")
async def publish_announcement(payload: FreePayload, db: Session = Depends(get_db), current_user=Depends(require_user)):
    data = payload.model_dump()
    ann_id = str(data.get("id") or make_record_key("ann"))
    announcement = {"id": ann_id, "title": data.get("title") or "Announcement", "content": data.get("content", ""), "date": utc_now_iso(), **data}
    store = JsonStore(db)
    store.upsert("forum", "announcement", ann_id, announcement)
    post_id = make_record_key("post-ann")
    store.upsert(
        "forum",
        "post",
        post_id,
        {
            "id": post_id,
            "title": announcement["title"],
            "content": announcement.get("content", ""),
            "author": "system",
            "avatar": "",
            "category": "qna",
            "categoryLabel": "Course Q&A",
            "tags": ["announcement"],
            "likes": 0,
            "isLiked": False,
            "views": 1,
            "createdAt": utc_now_iso(),
            "replies": [],
        },
    )
    return ok(announcement)


@router.get("/forum/hottopics")
async def get_hot_topics(db: Session = Depends(get_db)):
    return ok(JsonStore(db).list_payloads("forum", "hot_topic"))


@router.post("/forum/hottopics")
async def add_hot_topic(payload: FreePayload, db: Session = Depends(get_db), current_user=Depends(require_user)):
    tag = str(payload.model_dump().get("tag") or "").strip()
    if not tag:
        return ok(JsonStore(db).list_payloads("forum", "hot_topic"))
    store = JsonStore(db)
    store.upsert("forum", "hot_topic", tag, {"id": tag, "tag": tag, "count": 10})
    return ok(store.list_payloads("forum", "hot_topic"))


@router.put("/forum/hottopics/weight")
async def update_hot_topic_weight(payload: FreePayload, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    data = payload.model_dump()
    tag = str(data.get("tag") or "")
    change = int(data.get("change") or 0)
    store = JsonStore(db)
    topic = store.get_payload("forum", "hot_topic", tag) or {"id": tag, "tag": tag, "count": 0}
    topic["count"] = max(0, int(topic.get("count") or 0) + change)
    store.upsert("forum", "hot_topic", tag, topic)
    return ok(store.list_payloads("forum", "hot_topic"))


@router.delete("/forum/hottopics")
async def delete_hot_topic(tag: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    store = JsonStore(db)
    store.delete("forum", "hot_topic", tag)
    return ok(store.list_payloads("forum", "hot_topic"))


@router.get("/forum/ai-replies/logs")
async def get_ai_reply_logs(db: Session = Depends(get_db)):
    return ok(JsonStore(db).list_payloads("forum", "ai_reply_log"))


@router.put("/forum/ai-replies/logs/{log_id}")
async def audit_ai_reply(log_id: str, payload: FreePayload, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    store = JsonStore(db)
    data = payload.model_dump()
    log = store.patch("forum", "ai_reply_log", log_id, data) or {"id": log_id, **data}
    if data.get("content") and log.get("postId") and log.get("replyId"):
        post = store.get_payload("forum", "post", log["postId"])
        if post:
            for reply in post.get("replies") or []:
                if reply.get("id") == log.get("replyId"):
                    reply["content"] = data["content"]
            store.upsert("forum", "post", post["id"], post)
    return ok({"success": True})
