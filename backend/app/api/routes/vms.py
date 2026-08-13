import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.vm import VMCreate, VMRead, VMStats
from app.services import vm_service
from app.services.docker_service import DockerUnavailable

router = APIRouter(prefix="/api/vms", tags=["vms"])


def _get_or_404(db: Session, vm_id: uuid.UUID):
    vm = vm_service.get_vm(db, vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    return vm


@router.get("", response_model=list[VMRead])
def list_vms(db: Session = Depends(get_db)):
    return vm_service.list_vms(db)


@router.post("", response_model=VMRead, status_code=status.HTTP_201_CREATED)
def create_vm(payload: VMCreate, db: Session = Depends(get_db)):
    try:
        return vm_service.create_vm(db, payload)
    except DockerUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Container creation failed: {exc}") from exc


@router.get("/{vm_id}", response_model=VMRead)
def get_vm(vm_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, vm_id)


@router.get("/{vm_id}/stats", response_model=VMStats)
def get_vm_stats(vm_id: uuid.UUID, db: Session = Depends(get_db)):
    vm = _get_or_404(db, vm_id)
    try:
        return vm_service.vm_stats(vm)
    except DockerUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{vm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vm(vm_id: uuid.UUID, db: Session = Depends(get_db)):
    vm = _get_or_404(db, vm_id)
    vm_service.delete_vm(db, vm)


@router.post("/{vm_id}/start", response_model=VMRead)
def start_vm(vm_id: uuid.UUID, db: Session = Depends(get_db)):
    return _lifecycle(db, vm_id, vm_service.start_vm)


@router.post("/{vm_id}/stop", response_model=VMRead)
def stop_vm(vm_id: uuid.UUID, db: Session = Depends(get_db)):
    return _lifecycle(db, vm_id, vm_service.stop_vm)


@router.post("/{vm_id}/restart", response_model=VMRead)
def restart_vm(vm_id: uuid.UUID, db: Session = Depends(get_db)):
    return _lifecycle(db, vm_id, vm_service.restart_vm)


def _lifecycle(db: Session, vm_id: uuid.UUID, fn):
    vm = _get_or_404(db, vm_id)
    try:
        return fn(db, vm)
    except DockerUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
