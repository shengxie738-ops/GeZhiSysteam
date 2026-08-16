from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_chinese_datetime(value: datetime | None = None) -> str:
    current = value or datetime.now().astimezone()
    if current.tzinfo is not None:
        current = current.astimezone()
    return f"{current.year}年{current.month}月{current.day}日{current.hour:02d}点{current.minute:02d}分"
