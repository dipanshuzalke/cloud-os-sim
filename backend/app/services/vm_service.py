from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.vm import VM
from app.schemas.vm import VMCreate
from app.services import docker_service
from app.services.docker_service import DockerUnavailable

_DOCKER_TO_VM_STATUS = {
    "running": "running",
    "restarting": "restarting",
    "paused": "stopped",
    "exited": "stopped",
    "created": "stopped",
    "dead": "failed",
    "removing": "stopped",
    "missing": "failed",
}


def _sync(db: Session, vm: VM) -> VM:
    """Docker is the runtime source of truth; reconcile the database with it."""
    if not vm.container_id:
        return vm
    status = docker_service.container_status(vm.container_id)
    if status is None:
        return vm
    mapped = _DOCKER_TO_VM_STATUS.get(status, vm.status)
    if mapped != vm.status:
        vm.status = mapped
        db.commit()
        db.refresh(vm)
    return vm


def list_vms(db: Session, sync: bool = True) -> list[VM]:
    vms = list(db.scalars(select(VM).order_by(VM.created_at.desc())))
    if sync and docker_service.docker_available():
        for vm in vms:
            _sync(db, vm)
    return vms


def get_vm(db: Session, vm_id: uuid.UUID, sync: bool = True) -> VM | None:
    vm = db.get(VM, vm_id)
    if vm and sync:
        _sync(db, vm)
    return vm


def create_vm(db: Session, payload: VMCreate) -> VM:
    vm = VM(
        name=payload.name,
        cpu=payload.cpu,
        ram=payload.ram,
        storage=payload.storage,
        status="creating",
    )
    db.add(vm)
    db.commit()
    db.refresh(vm)

    if not docker_service.docker_available():
        # Phase 2 fallback: database-only VM, honestly reported as not containerised.
        vm.status = "running"
        vm.error = None
        db.commit()
        db.refresh(vm)
        return vm

    try:
        info = docker_service.create_container(
            vm_id=str(vm.id), vm_name=vm.name, cpu=vm.cpu, ram_mb=vm.ram
        )
    except (DockerUnavailable, Exception) as exc:  # noqa: BLE001
        vm.status = "failed"
        vm.error = str(exc)[:500]
        db.commit()
        db.refresh(vm)
        raise

    vm.container_id = info["container_id"]
    vm.container_name = info["container_name"]
    vm.volume_name = info["volume_name"]
    vm.image = info["image"]
    vm.status = _DOCKER_TO_VM_STATUS.get(info["status"], "running")
    try:
        db.commit()
    except Exception:
        # Never leave an orphan container behind if persistence fails.
        db.rollback()
        docker_service.remove_container(info["container_id"], info["volume_name"])
        raise
    db.refresh(vm)
    return vm


def delete_vm(db: Session, vm: VM) -> None:
    if vm.container_id and docker_service.docker_available():
        docker_service.remove_container(vm.container_id, vm.volume_name)
    db.delete(vm)
    db.commit()


def _lifecycle(db: Session, vm: VM, action: str) -> VM:
    if vm.container_id:
        fn = {
            "start": docker_service.start_container,
            "stop": docker_service.stop_container,
            "restart": docker_service.restart_container,
        }[action]
        status = fn(vm.container_id)
        vm.status = _DOCKER_TO_VM_STATUS.get(status, vm.status)
    else:
        vm.status = "stopped" if action == "stop" else "running"
    db.commit()
    db.refresh(vm)
    return vm


def start_vm(db: Session, vm: VM) -> VM:
    return _lifecycle(db, vm, "start")


def stop_vm(db: Session, vm: VM) -> VM:
    return _lifecycle(db, vm, "stop")


def restart_vm(db: Session, vm: VM) -> VM:
    return _lifecycle(db, vm, "restart")


def vm_stats(vm: VM) -> dict:
    if not vm.container_id:
        return {
            "container_id": None,
            "container_name": None,
            "container_status": None,
            "cpu_limit": None,
            "memory_limit_mb": None,
        }
    return docker_service.get_container_stats(vm.container_id)
