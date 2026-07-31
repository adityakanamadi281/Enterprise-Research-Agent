from sqlalchemy.orm import Session

from app.domain.models import AuditLog


def record_audit(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: str,
    request_id: str | None,
    **metadata: object,
) -> None:
    db.add(
        AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            metadata_json=metadata,
        )
    )
    db.commit()
