from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any


MINIPROGRAM_HEADER = "X-Gezhi-Client"
MINIPROGRAM_CLIENT_VALUES = {"miniprogram", "wechat-miniprogram", "weapp"}


def is_miniprogram_client(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().lower() in MINIPROGRAM_CLIENT_VALUES


def api_response(data: Any = None, message: str = "ok", code: int = 0) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def isoformat_z(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    if "T" in text and (text.endswith("Z") or "+" in text):
        return text
    return text.replace(" ", "T") + "Z" if " " in text else text


def page_items(items: list[dict[str, Any]], *, cursor: str | None = None, limit: int = 20) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit or 20), 100))
    start = 0
    if cursor:
        for index, item in enumerate(items):
            if str(item.get("id")) == str(cursor):
                start = index + 1
                break
    page = items[start:start + safe_limit]
    next_cursor = None
    if start + safe_limit < len(items) and page:
        next_cursor = str(page[-1].get("id"))
    return {"items": page, "nextCursor": next_cursor}
