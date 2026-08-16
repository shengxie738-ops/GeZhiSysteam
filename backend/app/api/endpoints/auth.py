from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.miniprogram_response import api_response, is_miniprogram_client
from app.core.responses import auth_fail, auth_ok
from app.core.security import create_access_token, decode_access_token, get_password_hash, verify_password
from app.models.student_profile import StudentProfile
from app.models.user_account import UserAccount
from app.services.sms_service import is_valid_phone, send_sms_code, verify_sms_code

router = APIRouter()


Role = Literal["student", "teacher"]
SmsPurpose = Literal["register", "login"]


class LoginRequest(BaseModel):
    username: str
    password: str
    role: Role


class RegisterRequest(BaseModel):
    username: str = ""
    password: str
    phone: str = ""
    role: Role
    confirm_password: Optional[str] = None
    sms_code: Optional[str] = None
    teacher_id: Optional[str] = None
    real_name: Optional[str] = None
    student_id: Optional[str] = None
    class_name: Optional[str] = None


class SmsSendRequest(BaseModel):
    phone: str
    purpose: SmsPurpose
    role: Role = "student"


class MobileLoginRequest(BaseModel):
    phone: str
    sms_code: str
    role: Role


def serialize_gitea_summary(db: Session, account: UserAccount) -> dict:
    try:
        from app.services.gitea_account_service import get_gitea_binding_summary

        return get_gitea_binding_summary(db, account)
    except Exception as exc:
        return {
            "username": "",
            "email": "",
            "syncStatus": "mock",
            "tokenLastFour": "",
            "syncError": str(exc),
        }


def serialize_user(db: Session, account: UserAccount) -> dict:
    real_name = account.real_name or ""
    phone = account.phone or ""
    avatar_url = f"/static/avatars/{account.avatar_path}" if account.avatar_path else ""
    student_id = account.student_id or ""
    teacher_id = account.teacher_id or ""
    class_name = account.class_name or ""
    return {
        "username": account.username,
        "role": account.role or "student",
        # camelCase（与业务模块统一）
        "realName": real_name,
        "phone": phone,
        "avatarUrl": avatar_url,
        "studentId": student_id,
        "teacherId": teacher_id,
        "className": class_name,
        # snake_case 别名（兼容现有前端）
        "real_name": real_name,
        "avatar_url": avatar_url,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "class_name": class_name,
        "gitea": serialize_gitea_summary(db, account),
    }


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _register_student(db: Session, data: RegisterRequest):
    real_name = _clean(data.real_name)
    student_id = _clean(data.student_id)
    class_name = _clean(data.class_name)
    phone = _clean(data.phone)
    sms_code = _clean(data.sms_code)

    if not real_name:
        return auth_fail("学生名不能为空")
    if not student_id:
        return auth_fail("学号不能为空")
    if not class_name:
        return auth_fail("班级号不能为空")
    if not is_valid_phone(phone):
        return auth_fail("请输入正确的11位手机号码")
    if data.confirm_password is not None and data.password != data.confirm_password:
        return auth_fail("两次密码输入不一致")
    if len(data.password) < 6:
        return auth_fail("password must be at least 6 characters")
    if not sms_code:
        return auth_fail("请先完成手机号验证")

    existing = (
        db.query(UserAccount)
        .filter(
            or_(
                UserAccount.username == student_id,
                UserAccount.student_id == student_id,
                UserAccount.phone == phone,
            )
        )
        .first()
    )
    if existing:
        if existing.phone == phone:
            return auth_fail("手机号已绑定")
        return auth_fail("学号已注册")

    verified, verify_message = verify_sms_code(db, phone, "register", sms_code)
    if not verified:
        return auth_fail(verify_message)

    account = UserAccount(
        username=student_id,
        role="student",
        phone=phone,
        real_name=real_name,
        student_id=student_id,
        teacher_id="",
        class_name=class_name,
        password_hash=get_password_hash(data.password),
    )
    db.add(account)
    db.add(StudentProfile(user_id=account.username))
    db.commit()
    return auth_ok(message="register success")


def _register(db: Session, data: RegisterRequest, role: Role):
    if data.role != role:
        return auth_fail("role mismatch")
    if role == "student":
        return _register_student(db, data)

    if role == "teacher" and not data.teacher_id:
        return auth_fail("teacher_id is required")
    if not _clean(data.username):
        return auth_fail("username is required")
    if data.confirm_password is not None and data.password != data.confirm_password:
        return auth_fail("两次密码输入不一致")
    if len(data.password) < 6:
        return auth_fail("password must be at least 6 characters")

    username = _clean(data.username)
    existing = db.query(UserAccount).filter(UserAccount.username == username).first()
    if existing:
        if existing.role != role:
            return auth_fail(f"this username is already registered as {existing.role}")
        return auth_fail("username already exists")

    account = UserAccount(
        username=username,
        role=role,
        phone=_clean(data.phone),
        real_name=_clean(data.real_name),
        student_id=_clean(data.student_id),
        teacher_id=_clean(data.teacher_id),
        class_name=_clean(data.class_name),
        password_hash=get_password_hash(data.password),
    )
    db.add(account)

    db.commit()
    return auth_ok(message="register success")


def _login(db: Session, data: LoginRequest, role: Role):
    if data.role != role:
        return auth_fail("role mismatch")

    account = db.query(UserAccount).filter(
        or_(
            UserAccount.username == data.username,
            UserAccount.phone == data.username,
            and_(UserAccount.teacher_id == data.username, UserAccount.role == "teacher"),
        )
    ).first()
    if not account:
        return auth_fail("username or password is incorrect")
    if account.role != role:
        return auth_fail(f"this account is registered as {account.role}")
    if not account.password_hash:
        account.password_hash = get_password_hash(data.password)
        db.commit()
        db.refresh(account)
    elif not verify_password(data.password, account.password_hash):
        return auth_fail("username or password is incorrect")

    token = create_access_token(account.username, account.role)
    return auth_ok(
        message="login success",
        data={
            "token": token,
            "user": serialize_user(db, account),
        },
    )


def _send_code(db: Session, data: SmsSendRequest):
    phone = _clean(data.phone)
    if not is_valid_phone(phone):
        return auth_fail("请输入正确的11位手机号码")

    if data.purpose == "register":
        existing = db.query(UserAccount).filter(UserAccount.phone == phone).first()
        if existing:
            return auth_fail("手机号已绑定")
    elif data.purpose == "login":
        existing = db.query(UserAccount).filter(
            UserAccount.phone == phone,
            UserAccount.role == data.role,
        ).first()
        if not existing:
            return auth_fail("该手机号未注册")

    sent, message, payload = send_sms_code(db, phone, data.purpose)
    if not sent:
        return auth_fail(message)
    return auth_ok(data=payload, message=message)


def _mobile_login(db: Session, data: MobileLoginRequest, role: Role):
    if data.role != role:
        return auth_fail("role mismatch")

    phone = _clean(data.phone)
    if not is_valid_phone(phone):
        return auth_fail("请输入正确的11位手机号码")

    account = db.query(UserAccount).filter(
        UserAccount.phone == phone,
        UserAccount.role == role,
    ).first()
    if not account:
        return auth_fail("该手机号未注册")

    verified, verify_message = verify_sms_code(db, phone, "login", data.sms_code)
    if not verified:
        return auth_fail(verify_message)

    token = create_access_token(account.username, account.role)
    return auth_ok(
        message="login success",
        data={
            "token": token,
            "user": serialize_user(db, account),
        },
    )


@router.post("/sms/send-code")
async def sms_send_code(data: SmsSendRequest, db: Session = Depends(get_db)):
    return _send_code(db, data)


@router.post("/student/register")
async def student_register(data: RegisterRequest, db: Session = Depends(get_db)):
    return _register(db, data, "student")


@router.post("/student/login")
async def student_login(
    data: LoginRequest,
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
    db: Session = Depends(get_db),
):
    result = _login(db, data, "student")
    if is_miniprogram_client(x_gezhi_client) and isinstance(result, dict) and result.get("success"):
        return api_response(result.get("data"))
    return result


@router.post("/student/mobile-login")
async def student_mobile_login(
    data: MobileLoginRequest,
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
    db: Session = Depends(get_db),
):
    result = _mobile_login(db, data, "student")
    if is_miniprogram_client(x_gezhi_client) and isinstance(result, dict) and result.get("success"):
        return api_response(result.get("data"))
    return result


@router.post("/teacher/register")
async def teacher_register(data: RegisterRequest, db: Session = Depends(get_db)):
    return _register(db, data, "teacher")


@router.post("/teacher/login")
async def teacher_login(
    data: LoginRequest,
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
    db: Session = Depends(get_db),
):
    result = _login(db, data, "teacher")
    if is_miniprogram_client(x_gezhi_client) and isinstance(result, dict) and result.get("success"):
        return api_response(result.get("data"))
    return result


@router.post("/teacher/mobile-login")
async def teacher_mobile_login(
    data: MobileLoginRequest,
    x_gezhi_client: str | None = Header(default=None, alias="X-Gezhi-Client"),
    db: Session = Depends(get_db),
):
    result = _mobile_login(db, data, "teacher")
    if is_miniprogram_client(x_gezhi_client) and isinstance(result, dict) and result.get("success"):
        return api_response(result.get("data"))
    return result


@router.get("/auth/me")
async def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        return auth_fail("not authenticated")
    payload = decode_access_token(authorization.split(" ", 1)[1])
    if not payload:
        return auth_fail("invalid token")
    account = db.query(UserAccount).filter(UserAccount.username == payload.get("sub")).first()
    if not account:
        return auth_fail("user not found")
    return auth_ok(data=serialize_user(db, account))
