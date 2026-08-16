import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.sms_verification_code import SmsVerificationCode


VALID_PURPOSES = {"register", "login"}
PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_phone(phone: str) -> str:
    return (phone or "").strip()


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_PATTERN.fullmatch(_normalize_phone(phone)))


def _hash_code(phone: str, purpose: str, code: str) -> str:
    payload = f"{phone}:{purpose}:{code}".encode("utf-8")
    return hmac.new(settings.APP_SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _latest_unconsumed(db: Session, phone: str, purpose: str) -> SmsVerificationCode | None:
    return (
        db.query(SmsVerificationCode)
        .filter(
            SmsVerificationCode.phone == phone,
            SmsVerificationCode.purpose == purpose,
            SmsVerificationCode.consumed_at.is_(None),
        )
        .order_by(SmsVerificationCode.sent_at.desc(), SmsVerificationCode.id.desc())
        .first()
    )


def _send_via_aliyun(phone: str, code: str) -> tuple[bool, str]:
    if not settings.ALIYUN_SMS_ACCESS_KEY_ID or not settings.ALIYUN_SMS_ACCESS_KEY_SECRET:
        return False, "短信服务未配置"
    if not settings.ALIYUN_SMS_SIGN_NAME or not settings.ALIYUN_SMS_TEMPLATE_CODE:
        return False, "短信模板未配置"

    try:
        from alibabacloud_dypnsapi20170525.client import Client as DypnsapiClient
        from alibabacloud_dypnsapi20170525 import models as dypnsapi_models
        from alibabacloud_tea_openapi import models as open_api_models
    except Exception:
        return False, "短信 SDK 未安装"

    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_SMS_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_SMS_ACCESS_KEY_SECRET,
    )
    config.endpoint = settings.ALIYUN_SMS_ENDPOINT
    client = DypnsapiClient(config)
    request = dypnsapi_models.SendSmsVerifyCodeRequest(
        phone_number=phone,
        sign_name=settings.ALIYUN_SMS_SIGN_NAME,
        template_code=settings.ALIYUN_SMS_TEMPLATE_CODE,
        template_param=json.dumps(
            {"code": code, "min": str(settings.SMS_CODE_EXPIRE_MINUTES)},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        out_id=f"{int(time.time() * 1000)}{secrets.randbelow(1000):03d}",
    )

    try:
        response = client.send_sms_verify_code(request)
    except Exception:
        return False, "短信发送失败"

    body = getattr(response, "body", None)
    response_code = getattr(body, "code", "")
    if str(response_code).upper() == "OK":
        return True, "验证码已发送"
    return False, getattr(body, "message", "短信发送失败")


def send_sms_code(db: Session, phone: str, purpose: str) -> tuple[bool, str, dict[str, Any]]:
    phone = _normalize_phone(phone)
    purpose = (purpose or "").strip()
    now = _utc_now()

    if purpose not in VALID_PURPOSES:
        return False, "验证码用途不正确", {}
    if not is_valid_phone(phone):
        return False, "请输入正确的11位手机号码", {}

    latest = _latest_unconsumed(db, phone, purpose)
    if latest and latest.sent_at + timedelta(seconds=settings.SMS_SEND_COOLDOWN_SECONDS) > now:
        return False, f"请稍后再获取验证码（{settings.SMS_SEND_COOLDOWN_SECONDS}秒内只能发送一次）", {}

    code = _generate_code()
    if settings.SMS_MOCK_ENABLED:
        sent = True
        send_message = "验证码已发送"
        payload: dict[str, Any] = {"mock": True, "debug_code": code}
    else:
        sent, send_message = _send_via_aliyun(phone, code)
        payload = {"mock": False}

    if not sent:
        return False, send_message, {}

    record = SmsVerificationCode(
        phone=phone,
        purpose=purpose,
        code_hash=_hash_code(phone, purpose, code),
        sent_at=now,
        expires_at=now + timedelta(minutes=settings.SMS_CODE_EXPIRE_MINUTES),
        attempts=0,
    )
    db.add(record)
    db.commit()
    return True, send_message, payload


def verify_sms_code(db: Session, phone: str, purpose: str, code: str) -> tuple[bool, str]:
    phone = _normalize_phone(phone)
    purpose = (purpose or "").strip()
    code = (code or "").strip()
    now = _utc_now()

    if purpose not in VALID_PURPOSES:
        return False, "验证码用途不正确"
    if not is_valid_phone(phone):
        return False, "请输入正确的11位手机号码"
    if not re.fullmatch(r"\d{6}", code):
        return False, "验证码错误"

    record = _latest_unconsumed(db, phone, purpose)
    if not record or record.expires_at < now:
        if record:
            record.consumed_at = now
            db.commit()
        return False, "验证码不存在或已失效"

    if record.attempts >= settings.SMS_MAX_VERIFY_ATTEMPTS:
        record.consumed_at = now
        db.commit()
        return False, "验证码不存在或已失效"

    if not hmac.compare_digest(record.code_hash, _hash_code(phone, purpose, code)):
        record.attempts += 1
        if record.attempts >= settings.SMS_MAX_VERIFY_ATTEMPTS:
            record.consumed_at = now
        db.commit()
        return False, "验证码错误"

    record.consumed_at = now
    db.commit()
    return True, "验证通过"
