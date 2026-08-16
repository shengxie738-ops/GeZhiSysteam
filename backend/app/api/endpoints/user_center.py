import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password
from app.models.user_account import UserAccount

router = APIRouter()


class UserInfoUpdate(BaseModel):
    username: str
    real_name: Optional[str] = None
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    class_name: Optional[str] = None
    phone: Optional[str] = None


class PasswordChange(BaseModel):
    username: str
    old_password: str
    new_password: str


def get_or_create_account(db: Session, username: str) -> UserAccount:
    account = db.query(UserAccount).filter(UserAccount.username == username).first()
    if not account:
        account = UserAccount(username=username, role="student", password_hash="")
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


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


def serialize_account(db: Session, account: UserAccount) -> dict:
    return {
        "username": account.username,
        "role": account.role or "student",
        "real_name": account.real_name or "",
        "phone": account.phone or "",
        "student_id": account.student_id or "",
        "teacher_id": account.teacher_id or "",
        "class_name": account.class_name or "",
        "avatar_url": f"/static/avatars/{account.avatar_path}" if account.avatar_path else "",
        "gitea": serialize_gitea_summary(db, account),
    }


@router.get("/user/info/{username}")
async def get_user_info(username: str, db: Session = Depends(get_db)):
    account = get_or_create_account(db, username)
    return serialize_account(db, account)


@router.post("/user/update_info")
async def update_user_info(data: UserInfoUpdate, db: Session = Depends(get_db)):
    account = get_or_create_account(db, data.username)

    for field in ("real_name", "student_id", "teacher_id", "class_name", "phone"):
        value = getattr(data, field)
        if value is not None:
            setattr(account, field, value.strip())

    db.commit()
    db.refresh(account)
    return {
        "status": "success",
        "message": "profile updated",
        "user": serialize_account(db, account),
    }


@router.post("/user/change_password")
async def change_password(data: PasswordChange, db: Session = Depends(get_db)):
    account = get_or_create_account(db, data.username)

    if account.password_hash and not verify_password(data.old_password, account.password_hash):
        raise HTTPException(status_code=400, detail="old password is incorrect")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="new password must be at least 6 characters")

    account.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"status": "success", "message": "password updated"}


@router.post("/user/upload_avatar")
async def upload_avatar(
    username: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="only JPG / PNG / GIF / WebP images are supported")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="image size must not exceed 2MB")

    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static")
    avatar_dir = os.path.join(static_dir, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)

    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    ext = ext_map.get(file.content_type, ".jpg")
    filename = f"{username}{ext}"
    filepath = os.path.join(avatar_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    account = get_or_create_account(db, username)
    account.avatar_path = filename
    db.commit()
    db.refresh(account)

    return {
        "status": "success",
        "message": "avatar uploaded",
        "avatar_url": f"/static/avatars/{filename}",
        "user": serialize_account(db, account),
    }
