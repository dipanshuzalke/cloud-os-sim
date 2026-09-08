"""Phase 4 — resource monitoring.

Every second the collector reads `docker stats` for each running container,
persists a sample in PostgreSQL and broadcasts the fleet snapshot over
Socket.IO so the React charts update live (no polling).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.realtime import emit_metrics
from app.models.metric import VMMetric
from app.models.vm import VM
from app.services import docker_service

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 1.0
RETENTION_MINUTES = 60
_PRUNE_EVERY = 300  # ticks

_task: asyncio.Task | None = None
# container_id -> (rx_mb, tx_mb, timestamp) for rate calculation
_previous: dict[str, tuple[float, float, float]] = {}


def _rates(container_id: str, rx_mb: float, tx_mb: float, now: float) -> tuple[float, float]:
    prev = _previous.get(container_id)
    _previous[container_id] = (rx_mb, tx_mb, now)
    if not prev:
        return 0.0, 0.0
    dt = max(now - prev[2], 1e-3)
    rx_rate = max(rx_mb - prev[0], 0.0) * 1024 / dt  # KB/s
    tx_rate = max(tx_mb - prev[1], 0.0) * 1024 / dt
    return round(rx_rate, 2), round(tx_rate, 2)


def collect_once() -> dict:
    """Blocking work: read Docker stats and write samples. Runs in a thread."""
    now_ts = datetime.now(timezone.utc)
    samples: list[dict] = []

    if not docker_service.docker_available():
        return {
            "recorded_at": now_ts.isoformat(),
            "docker": False,
            "running_vms": 0,
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_usage_mb": 0.0,
            "network_rx_rate_kbps": 0.0,
            "network_tx_rate_kbps": 0.0,
            "vms": [],
        }

    db: Session = SessionLocal()
    try:
        vms = list(db.scalars(select(VM).where(VM.container_id.is_not(None))))
        for vm in vms:
            stats = docker_service.read_stats(vm.container_id or "")
            if not stats:
                continue
            rx_rate, tx_rate = _rates(
                vm.container_id or "",
                stats["network_rx_mb"],
                stats["network_tx_mb"],
                now_ts.timestamp(),
            )
            db.add(
                VMMetric(
                    vm_id=vm.id,
                    container_id=vm.container_id,
                    cpu_percent=stats["cpu_percent"],
                    memory_usage_mb=stats["memory_usage_mb"],
                    memory_limit_mb=stats["memory_limit_mb"],
                    memory_percent=stats["memory_percent"],
                    network_rx_mb=stats["network_rx_mb"],
                    network_tx_mb=stats["network_tx_mb"],
                    network_rx_rate_kbps=rx_rate,
                    network_tx_rate_kbps=tx_rate,
                    block_read_mb=stats["block_read_mb"],
                    block_write_mb=stats["block_write_mb"],
                    recorded_at=now_ts,
                )
            )
            samples.append(
                {
                    "vm_id": str(vm.id),
                    "name": vm.name,
                    "container_id": vm.container_id,
                    "network_rx_rate_kbps": rx_rate,
                    "network_tx_rate_kbps": tx_rate,
                    **stats,
                }
            )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("metric collection failed: %s", exc)
    finally:
        db.close()

    count = len(samples)
    return {
        "recorded_at": now_ts.isoformat(),
        "docker": True,
        "running_vms": count,
        "cpu_percent": round(sum(s["cpu_percent"] for s in samples) / count, 2) if count else 0.0,
        "memory_percent": round(sum(s["memory_percent"] for s in samples) / count, 2)
        if count
        else 0.0,
        "memory_usage_mb": round(sum(s["memory_usage_mb"] for s in samples), 2),
        "network_rx_rate_kbps": round(sum(s["network_rx_rate_kbps"] for s in samples), 2),
        "network_tx_rate_kbps": round(sum(s["network_tx_rate_kbps"] for s in samples), 2),
        "vms": samples,
    }


def prune_old() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=RETENTION_MINUTES)
    db: Session = SessionLocal()
    try:
        db.execute(delete(VMMetric).where(VMMetric.recorded_at < cutoff))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("metric prune failed: %s", exc)
    finally:
        db.close()


async def _loop() -> None:
    tick = 0
    while True:
        started = asyncio.get_running_loop().time()
        try:
            payload = await asyncio.to_thread(collect_once)
            await emit_metrics(payload)
            tick += 1
            if tick % _PRUNE_EVERY == 0:
                await asyncio.to_thread(prune_old)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("monitor loop error: %s", exc)
        elapsed = asyncio.get_running_loop().time() - started
        await asyncio.sleep(max(INTERVAL_SECONDS - elapsed, 0.1))


def start() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())
        logger.info("resource monitor started (%.0fs interval)", INTERVAL_SECONDS)


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
