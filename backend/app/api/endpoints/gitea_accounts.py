from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import ok
from app.core.security import decode_access_token
from app.models.user_account import UserAccount
from app.services.gitea_account_service import GiteaTokenError, create_or_rotate_gitea_token, ensure_gitea_account_for_user, gitea_email_for_account


router = APIRouter()


def resolve_account_from_authorization(db: Session, authorization: str | None) -> UserAccount:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    payload = decode_access_token(authorization.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="invalid token")
    account = db.query(UserAccount).filter(UserAccount.username == payload.get("sub")).first()
    if not account:
        raise HTTPException(status_code=404, detail="user not found")
    return account


def get_gitea_me_payload(db: Session, account: UserAccount) -> dict[str, Any]:
    identity = ensure_gitea_account_for_user(db, account)
    email = gitea_email_for_account(account)
    return {
        "campusUserId": account.username,
        "role": account.role or "student",
        "studentId": account.student_id or "",
        "teacherId": account.teacher_id or "",
        "className": account.class_name or "",
        "giteaUserId": identity.gitea_user_id,
        "giteaUsername": identity.gitea_username,
        "giteaEmail": identity.gitea_email,
        "syncStatus": identity.sync_status,
        "syncError": identity.sync_error,
        "tokenLastFour": identity.token_last_four,
        "gitConfigCommands": [
            f'git config user.name "{account.username}"',
            f'git config user.email "{email}"',
        ],
    }


@router.get("/gitea/me")
async def get_gitea_me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    account = resolve_account_from_authorization(db, authorization)
    return ok(get_gitea_me_payload(db, account))


@router.post("/gitea/token")
async def rotate_gitea_token(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    account = resolve_account_from_authorization(db, authorization)
    try:
        token = create_or_rotate_gitea_token(db, account)
    except GiteaTokenError as exc:
        raise HTTPException(status_code=502, detail=f"Gitea Token 生成失败：{exc}") from exc
    return ok(
        {
            "giteaUsername": token.gitea_username,
            "token": token.token,
            "tokenLastFour": token.token_last_four,
            "tokenCreatedAt": token.token_created_at,
            "warning": "此 Token 只显示一次，请保存到本机 Git 凭据管理器；丢失后可重新生成。",
        }
    )
