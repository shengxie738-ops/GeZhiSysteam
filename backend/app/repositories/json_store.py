import json
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.domain_record import DomainRecord


def make_record_key(prefix: str) -> str:
    return f"{prefix}-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


def load_payload(record: DomainRecord | None) -> dict[str, Any] | None:
    if not record:
        return None
    try:
        data = json.loads(record.payload)
    except Exception:
        data = {}
    if isinstance(data, dict):
        data.setdefault("id", record.record_key)
        return data
    return {"id": record.record_key, "value": data}


class JsonStore:
    def __init__(self, db: Session):
        self.db = db

    def list_payloads(
        self,
        module: str,
        record_type: str | None = None,
        owner_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self.db.query(DomainRecord).filter(DomainRecord.module == module)
        if record_type is not None:
            query = query.filter(DomainRecord.record_type == record_type)
        if owner_id is not None:
            query = query.filter(DomainRecord.owner_id == owner_id)
        if status is not None:
            query = query.filter(DomainRecord.status == status)
        records = query.order_by(DomainRecord.created_at.desc()).all()
        return [payload for payload in (load_payload(record) for record in records) if payload is not None]

    def get_record(
        self,
        module: str,
        record_type: str,
        record_key: str,
        owner_id: str | None = None,
    ) -> DomainRecord | None:
        query = self.db.query(DomainRecord).filter(
            DomainRecord.module == module,
            DomainRecord.record_type == record_type,
            DomainRecord.record_key == record_key,
        )
        if owner_id is not None:
            query = query.filter(DomainRecord.owner_id == owner_id)
        return query.order_by(DomainRecord.id.desc()).first()

    def get_payload(
        self,
        module: str,
        record_type: str,
        record_key: str,
        owner_id: str | None = None,
    ) -> dict[str, Any] | None:
        return load_payload(self.get_record(module, record_type, record_key, owner_id))

    def upsert(
        self,
        module: str,
        record_type: str,
        record_key: str,
        payload: dict[str, Any],
        owner_id: str = "",
        role: str = "",
        status: str = "",
    ) -> dict[str, Any]:
        record = self.get_record(module, record_type, record_key, owner_id=owner_id)
        payload = dict(payload or {})
        payload.setdefault("id", record_key)
        if not record:
            record = DomainRecord(
                module=module,
                record_type=record_type,
                record_key=record_key,
                owner_id=owner_id or "",
                role=role or "",
            )
            self.db.add(record)
        record.status = status or payload.get("status") or record.status or ""
        record.payload = json.dumps(payload, ensure_ascii=False, default=str)
        self.db.commit()
        self.db.refresh(record)
        return load_payload(record) or payload

    def create(
        self,
        module: str,
        record_type: str,
        payload: dict[str, Any],
        prefix: str,
        owner_id: str = "",
        role: str = "",
        status: str = "",
    ) -> dict[str, Any]:
        record_key = str((payload or {}).get("id") or make_record_key(prefix))
        return self.upsert(module, record_type, record_key, payload, owner_id=owner_id, role=role, status=status)

    def patch(
        self,
        module: str,
        record_type: str,
        record_key: str,
        patch: dict[str, Any],
        owner_id: str | None = None,
    ) -> dict[str, Any] | None:
        record = self.get_record(module, record_type, record_key, owner_id=owner_id)
        payload = load_payload(record)
        if not record or payload is None:
            return None
        payload.update(patch or {})
        return self.upsert(
            module,
            record_type,
            record.record_key,
            payload,
            owner_id=record.owner_id,
            role=record.role,
            status=payload.get("status") or record.status,
        )

    def delete(self, module: str, record_type: str, record_key: str) -> bool:
        record = self.get_record(module, record_type, record_key)
        if not record:
            return False
        self.db.delete(record)
        self.db.commit()
        return True
