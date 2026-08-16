from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
import re
import secrets
import string

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.gitea_account_binding import GiteaAccountBinding
from app.models.user_account import UserAccount
from app.services.gitea_service import GiteaService
from app.utils.datetime import utc_now_iso


class GiteaTokenError(Exception):
    """Raised when Gitea access token creation or rotation fails."""


@dataclass
class GiteaIdentity:
    campus_user_id: str
    role: str
    student_id: str
    teacher_id: str
    class_name: str
    gitea_user_id: int | None
    gitea_username: str
    gitea_email: str
    sync_status: str
    sync_error: str
    token_last_four: str = ""


@dataclass
class GiteaTokenResult:
    gitea_username: str
    token: str
    token_last_four: str
    token_created_at: str


@dataclass
class RepoPermission:
    campus_user_id: str
    permission: Literal["read", "write", "admin"]
    reason: str = ""


def _clean(value: str | None) -> str:
    return str(value or "").strip()


def _safe_part(value: str) -> str:
    part = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    part = re.sub(r"-{2,}", "-", part).strip("-._")
    return part or "user"


def _random_password(length: int = 28) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def gitea_username_for_account(account: UserAccount) -> str:
    if (account.role or "student") == "teacher":
        source = _clean(account.teacher_id) or _clean(account.username)
        return f"tea_{_safe_part(source)}"
    source = _clean(account.student_id) or _clean(account.username)
    return f"stu_{_safe_part(source)}"


def gitea_email_for_account(account: UserAccount) -> str:
    if (account.role or "student") == "teacher":
        source = _clean(account.teacher_id) or _clean(account.username)
        return f"teacher_{_safe_part(source)}@gezhi.local"
    source = _clean(account.student_id) or _clean(account.username)
    return f"{_safe_part(source)}@gezhi.local"


def _identity_from_binding(binding: GiteaAccountBinding) -> GiteaIdentity:
    return GiteaIdentity(
        campus_user_id=binding.campus_user_id,
        role=binding.role,
        student_id=binding.student_id,
        teacher_id=binding.teacher_id,
        class_name=binding.class_name,
        gitea_user_id=binding.gitea_user_id,
        gitea_username=binding.gitea_username,
        gitea_email=binding.gitea_email,
        sync_status=binding.sync_status,
        sync_error=binding.sync_error,
        token_last_four=binding.token_last_four,
    )


def _apply_account_fields(binding: GiteaAccountBinding, account: UserAccount, *, username: str, email: str) -> None:
    binding.role = account.role or "student"
    binding.student_id = account.student_id or ""
    binding.teacher_id = account.teacher_id or ""
    binding.class_name = account.class_name or ""
    binding.gitea_username = username
    binding.gitea_email = email


def get_gitea_binding_summary(db: Session, account: UserAccount) -> dict:
    """Read-only Gitea summary for login/user profile; does not call Gitea API."""
    binding = db.query(GiteaAccountBinding).filter(GiteaAccountBinding.campus_user_id == account.username).first()
    if binding:
        return {
            "username": binding.gitea_username,
            "email": binding.gitea_email,
            "syncStatus": binding.sync_status,
            "tokenLastFour": binding.token_last_four,
        }
    return {
        "username": gitea_username_for_account(account),
        "email": gitea_email_for_account(account),
        "syncStatus": "pending",
        "tokenLastFour": "",
    }


def _uses_real_gitea_api(client: GiteaService | object) -> bool:
    if hasattr(client, "enabled") and hasattr(client, "token"):
        return bool(client.enabled and client.token)
    return False


def ensure_gitea_account_for_user(
    db: Session,
    account: UserAccount,
    *,
    gitea: GiteaService | None = None,
    force_sync: bool = False,
) -> GiteaIdentity:
    client = gitea or GiteaService()
    username = gitea_username_for_account(account)
    email = gitea_email_for_account(account)
    binding = db.query(GiteaAccountBinding).filter(GiteaAccountBinding.campus_user_id == account.username).first()
    if not binding:
        binding = GiteaAccountBinding(
            campus_user_id=account.username,
            role=account.role or "student",
            student_id=account.student_id or "",
            teacher_id=account.teacher_id or "",
            class_name=account.class_name or "",
            gitea_username=username,
            gitea_email=email,
            sync_status="mock",
            sync_error="",
        )
        db.add(binding)

    _apply_account_fields(binding, account, username=username, email=email)

    if (
        not force_sync
        and binding.sync_status == "synced"
        and binding.gitea_user_id is not None
    ):
        db.commit()
        db.refresh(binding)
        return _identity_from_binding(binding)

    if (
        not force_sync
        and binding.sync_status == "mock"
        and binding.gitea_user_id is not None
        and _uses_real_gitea_api(client)
    ):
        org_error = binding.sync_error or ""
        try:
            client.ensure_org_membership(username, role="member")
            org_error = ""
        except Exception as org_exc:
            org_error = str(org_exc)
        binding.sync_status = "synced"
        binding.sync_error = org_error
        db.commit()
        db.refresh(binding)
        return _identity_from_binding(binding)

    if not _uses_real_gitea_api(client):
        if binding.sync_status != "synced" or binding.gitea_user_id is None:
            try:
                user = client.create_user(
                    username=username,
                    email=email,
                    full_name=account.real_name or account.username,
                    password=_random_password(),
                    must_change_password=False,
                )
                binding.gitea_user_id = user.get("id")
                if hasattr(client, "ensure_org_membership"):
                    client.ensure_org_membership(username, role="member")
                binding.sync_status = "synced" if user.get("id") is not None else "mock"
                binding.sync_error = ""
            except Exception as exc:
                binding.sync_status = "mock"
                binding.sync_error = str(exc)
        db.commit()
        db.refresh(binding)
        return _identity_from_binding(binding)

    try:
        user = client.create_user(
            username=username,
            email=email,
            full_name=account.real_name or account.username,
            password=_random_password(),
            must_change_password=False,
        )
        binding.gitea_user_id = user.get("id")
        org_error = ""
        try:
            client.ensure_org_membership(username, role="member")
        except Exception as org_exc:
            org_error = str(org_exc)
        binding.sync_status = "synced" if user.get("id") is not None else "mock"
        binding.sync_error = org_error
    except Exception as exc:
        existing = client.get_user(username) if hasattr(client, "get_user") else None
        if existing and existing.get("id") is not None:
            binding.gitea_user_id = existing.get("id")
            org_error = ""
            try:
                client.ensure_org_membership(username, role="member")
            except Exception as org_exc:
                org_error = str(org_exc)
            binding.sync_status = "synced"
            binding.sync_error = org_error
        else:
            binding.sync_status = "mock"
            binding.sync_error = str(exc)

    db.commit()
    db.refresh(binding)
    return _identity_from_binding(binding)


def ensure_gitea_account_by_username(db: Session, campus_user_id: str, *, gitea: GiteaService | None = None) -> GiteaIdentity | None:
    account = db.query(UserAccount).filter(UserAccount.username == campus_user_id).first()
    if not account:
        return None
    return ensure_gitea_account_for_user(db, account, gitea=gitea)


def create_or_rotate_gitea_token(db: Session, account: UserAccount, *, gitea: GiteaService | None = None) -> GiteaTokenResult:
    identity = ensure_gitea_account_for_user(db, account, gitea=gitea)
    token_name = "campus-learning-system"
    client = gitea or GiteaService()
    try:
        token = client.create_user_token(identity.gitea_username, token_name)
    except Exception as exc:
        raise GiteaTokenError(str(exc)) from exc
    if not token:
        raise GiteaTokenError("Gitea 未返回有效 Token")
    token_created_at = datetime.now(timezone.utc)
    token_created_at_iso = utc_now_iso()
    binding = db.query(GiteaAccountBinding).filter(GiteaAccountBinding.campus_user_id == account.username).one()
    binding.token_name = token_name
    binding.token_last_four = token[-4:] if token else ""
    binding.token_created_at = token_created_at
    db.commit()
    return GiteaTokenResult(
        gitea_username=identity.gitea_username,
        token=token,
        token_last_four=binding.token_last_four,
        token_created_at=token_created_at_iso,
    )


def ensure_repository_collaborators(
    db: Session,
    repo_owner: str,
    repo_name: str,
    permissions: list[RepoPermission],
    *,
    gitea: GiteaService | None = None,
) -> list[dict]:
    client = gitea or GiteaService()
    result = []
    for item in permissions:
        identity = ensure_gitea_account_by_username(db, item.campus_user_id, gitea=client)
        if not identity:
            result.append({"campusUserId": item.campus_user_id, "status": "missing_user", "permission": item.permission})
            continue
        try:
            client.add_repository_collaborator(
                owner=repo_owner,
                repo=repo_name,
                username=identity.gitea_username,
                permission=item.permission,
            )
            result.append({"campusUserId": item.campus_user_id, "giteaUsername": identity.gitea_username, "status": "synced", "permission": item.permission})
        except Exception as exc:
            result.append({"campusUserId": item.campus_user_id, "giteaUsername": identity.gitea_username, "status": "mock", "permission": item.permission, "error": str(exc)})
    return result


def match_campus_user_from_gitea_event(db: Session, *, sender_username: str = "", commit_author: dict | None = None) -> dict:
    author = commit_author or {}
    sender = _clean(sender_username)
    if sender:
        binding = db.query(GiteaAccountBinding).filter(GiteaAccountBinding.gitea_username == sender).first()
        if binding:
            account = db.query(UserAccount).filter(UserAccount.username == binding.campus_user_id).first()
            return {
                "campusUserId": binding.campus_user_id,
                "studentId": binding.student_id,
                "giteaUsername": binding.gitea_username,
                "displayName": (account.real_name if account and account.real_name else binding.campus_user_id),
                "matchSource": "gitea_username",
            }
    email = _clean(author.get("email") if isinstance(author, dict) else "")
    if email:
        binding = db.query(GiteaAccountBinding).filter(GiteaAccountBinding.gitea_email == email).first()
        if binding:
            account = db.query(UserAccount).filter(UserAccount.username == binding.campus_user_id).first()
            return {
                "campusUserId": binding.campus_user_id,
                "studentId": binding.student_id,
                "giteaUsername": binding.gitea_username,
                "displayName": (account.real_name if account and account.real_name else binding.campus_user_id),
                "matchSource": "gitea_email",
            }
        if email.lower().endswith("@gezhi.local"):
            local_part = email.split("@", 1)[0]
            if local_part.lower().startswith("teacher_"):
                teacher_key = local_part[len("teacher_") :]
                account = db.query(UserAccount).filter(
                    or_(UserAccount.teacher_id == teacher_key, UserAccount.username == teacher_key)
                ).first()
                if account:
                    return {
                        "campusUserId": account.username,
                        "studentId": account.student_id or "",
                        "giteaUsername": "",
                        "displayName": account.real_name or account.username,
                        "matchSource": "teacher_email",
                    }
            else:
                account = db.query(UserAccount).filter(UserAccount.student_id == local_part).first()
                if account:
                    return {
                        "campusUserId": account.username,
                        "studentId": account.student_id or "",
                        "giteaUsername": "",
                        "displayName": account.real_name or account.username,
                        "matchSource": "student_email",
                    }
    for candidate in (author.get("username"), author.get("name"), sender):
        value = _clean(candidate)
        if not value:
            continue
        account = db.query(UserAccount).filter(or_(UserAccount.username == value, UserAccount.real_name == value)).first()
        if account:
            return {
                "campusUserId": account.username,
                "studentId": account.student_id or "",
                "giteaUsername": "",
                "displayName": account.real_name or account.username,
                "matchSource": "legacy_user_account",
            }
    fallback = _clean(author.get("name") if isinstance(author, dict) else "") or sender or "unknown"
    return {"campusUserId": "", "studentId": "", "giteaUsername": sender, "displayName": f"{fallback} (未绑定 Gitea 用户)", "matchSource": "unmatched"}
