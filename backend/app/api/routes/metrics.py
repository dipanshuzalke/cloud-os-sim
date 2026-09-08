import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.metric import VMMetric
from app.models.vm import VM
from app.schemas.metric import MetricRead
from app.services import monitor_service

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/latest")
def latest_fleet_sample():
    """Immediate snapshot — the live stream is delivered over Socket.IO."""
    return monitor_service.collect_once()


@router.get("/{vm_id}", response_model=list[MetricRead])
def vm_history(
    vm_id: uuid.UUID,
    limit: int = Query(120, ge=1, le=3600),
    db: Session = Depends(get_db),
):
    if not db.get(VM, vm_id):
        raise HTTPException(status_code=404, detail="VM not found")
    rows = list(
        db.scalars(
            select(VMMetric)
            .where(VMMetric.vm_id == vm_id)
            .order_by(VMMetric.recorded_at.desc())
            .limit(limit)
        )
    )
    return list(reversed(rows))
