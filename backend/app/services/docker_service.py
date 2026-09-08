"""All Docker Engine interaction lives here.

Route handlers never touch the Docker SDK directly. If Docker is unavailable the
service degrades gracefully so Phase 2 (database-only) behaviour still works.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None
_client_error: str | None = None


class DockerUnavailable(RuntimeError):
    pass


def _sanitize(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "-", value).strip("-._")
    return cleaned[:40].lower() or "vm"


def container_name_for(vm_id: str, vm_name: str) -> str:
    return f"cloudos-vm-{_sanitize(vm_name)}-{str(vm_id)[:8]}"


def volume_name_for(vm_id: str) -> str:
    return f"cloudos-vol-{str(vm_id)[:8]}"


def get_client():
    """Lazily build the Docker client so the API boots without Docker present."""
    global _client, _client_error
    if not settings.docker_enabled:
        raise DockerUnavailable("Docker integration is disabled (DOCKER_ENABLED=false)")
    if _client is not None:
        return _client
    try:
        import docker  # imported lazily so the package stays optional at boot

        _client = (
            docker.DockerClient(base_url=settings.docker_host)
            if settings.docker_host
            else docker.from_env()
        )
        _client.ping()
        _client_error = None
        return _client
    except Exception as exc:  # noqa: BLE001
        _client = None
        _client_error = str(exc)
        raise DockerUnavailable(f"Cannot reach Docker Engine: {exc}") from exc


def docker_available() -> bool:
    try:
        get_client()
        return True
    except DockerUnavailable:
        return False


def ensure_image(image: str | None = None) -> str:
    client = get_client()
    image = image or settings.vm_base_image
    try:
        client.images.get(image)
    except Exception:  # noqa: BLE001 - image missing locally
        logger.info("Pulling image %s", image)
        client.images.pull(image)
    return image


def create_container(
    *, vm_id: str, vm_name: str, cpu: int, ram_mb: int, image: str | None = None
) -> dict[str, Any]:
    """Create (and start) a resource-limited container for a simulated VM."""
    client = get_client()
    image = ensure_image(image)
    name = container_name_for(vm_id, vm_name)
    volume = volume_name_for(vm_id)
    client.volumes.create(name=volume)

    container = client.containers.create(
        image=image,
        name=name,
        command=["sleep", "infinity"],
        detach=True,
        tty=True,
        # Enforced resource limits (not just stored in Postgres)
        nano_cpus=int(cpu * 1_000_000_000),
        mem_limit=f"{ram_mb}m",
        # Safe defaults: no privileges, no docker socket, no host network
        privileged=False,
        network_mode="bridge",
        cap_drop=["ALL"],
        security_opt=["no-new-privileges:true"],
        volumes={volume: {"bind": "/data", "mode": "rw"}},
        labels={"managed-by": "cloudos", "cloudos.vm_id": str(vm_id)},
    )
    container.start()
    container.reload()
    return {
        "container_id": container.id,
        "container_name": container.name,
        "volume_name": volume,
        "image": image,
        "status": container.status,
    }


def get_container(container_id: str):
    return get_client().containers.get(container_id)


def list_containers() -> list[dict[str, Any]]:
    client = get_client()
    return [
        {"id": c.id, "name": c.name, "status": c.status}
        for c in client.containers.list(all=True, filters={"label": "managed-by=cloudos"})
    ]


def start_container(container_id: str) -> str:
    c = get_container(container_id)
    c.start()
    c.reload()
    return c.status


def stop_container(container_id: str, timeout: int = 10) -> str:
    c = get_container(container_id)
    c.stop(timeout=timeout)
    c.reload()
    return c.status


def restart_container(container_id: str, timeout: int = 10) -> str:
    c = get_container(container_id)
    c.restart(timeout=timeout)
    c.reload()
    return c.status


def remove_container(container_id: str, volume_name: str | None = None) -> None:
    client = get_client()
    try:
        c = client.containers.get(container_id)
        try:
            c.stop(timeout=10)
        except Exception:  # noqa: BLE001 - already stopped
            pass
        c.remove(force=True)
    except Exception as exc:  # noqa: BLE001 - container already gone
        logger.warning("remove_container: %s", exc)
    if volume_name:
        try:
            client.volumes.get(volume_name).remove(force=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("remove_volume: %s", exc)


def container_status(container_id: str) -> str | None:
    try:
        c = get_container(container_id)
        return c.status
    except DockerUnavailable:
        return None
    except Exception:  # noqa: BLE001 - container missing
        return "missing"


def get_container_stats(container_id: str) -> dict[str, Any]:
    c = get_container(container_id)
    c.reload()
    host = c.attrs.get("HostConfig", {})
    nano = host.get("NanoCpus") or 0
    mem = host.get("Memory") or 0
    result: dict[str, Any] = {
        "container_id": c.id,
        "container_name": c.name,
        "container_status": c.status,
        "cpu_limit": (nano / 1_000_000_000) if nano else None,
        "memory_limit_mb": int(mem / (1024 * 1024)) if mem else None,
        "cpu_percent": None,
        "memory_usage_mb": None,
    }
    if c.status == "running":
        try:
            s = c.stats(stream=False)
            cpu_delta = (
                s["cpu_stats"]["cpu_usage"]["total_usage"]
                - s["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            sys_delta = s["cpu_stats"]["system_cpu_usage"] - s["precpu_stats"]["system_cpu_usage"]
            online = s["cpu_stats"].get("online_cpus") or 1
            if sys_delta > 0:
                result["cpu_percent"] = round((cpu_delta / sys_delta) * online * 100, 2)
            result["memory_usage_mb"] = round(s["memory_stats"].get("usage", 0) / (1024 * 1024), 2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("stats: %s", exc)
    return result


def _cpu_percent(s: dict[str, Any]) -> float:
    try:
        cpu = s["cpu_stats"]
        pre = s["precpu_stats"]
        cpu_delta = cpu["cpu_usage"]["total_usage"] - pre["cpu_usage"]["total_usage"]
        sys_delta = (cpu.get("system_cpu_usage") or 0) - (pre.get("system_cpu_usage") or 0)
        online = cpu.get("online_cpus") or len(cpu["cpu_usage"].get("percpu_usage") or [1]) or 1
        if sys_delta > 0 and cpu_delta > 0:
            return round((cpu_delta / sys_delta) * online * 100, 2)
    except Exception:  # noqa: BLE001
        pass
    return 0.0


_MB = 1024 * 1024


def read_stats(container_id: str) -> dict[str, Any] | None:
    """One `docker stats` sample: CPU, memory, network and block IO.

    Returns None when the container is gone or not running.
    """
    try:
        c = get_container(container_id)
        c.reload()
        if c.status != "running":
            return None
        s = c.stats(stream=False)
    except DockerUnavailable:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("read_stats(%s): %s", container_id, exc)
        return None

    mem = s.get("memory_stats", {}) or {}
    usage = mem.get("usage", 0) - (mem.get("stats", {}) or {}).get("cache", 0)
    limit = mem.get("limit", 0) or 0

    rx = tx = 0
    for iface in (s.get("networks") or {}).values():
        rx += iface.get("rx_bytes", 0)
        tx += iface.get("tx_bytes", 0)

    read_b = write_b = 0
    for entry in ((s.get("blkio_stats") or {}).get("io_service_bytes_recursive") or []):
        op = str(entry.get("op", "")).lower()
        if op == "read":
            read_b += entry.get("value", 0)
        elif op == "write":
            write_b += entry.get("value", 0)

    usage_mb = round(max(usage, 0) / _MB, 2)
    limit_mb = round(limit / _MB, 2)
    return {
        "container_id": container_id,
        "cpu_percent": _cpu_percent(s),
        "memory_usage_mb": usage_mb,
        "memory_limit_mb": limit_mb,
        "memory_percent": round((usage_mb / limit_mb) * 100, 2) if limit_mb else 0.0,
        "network_rx_mb": round(rx / _MB, 3),
        "network_tx_mb": round(tx / _MB, 3),
        "block_read_mb": round(read_b / _MB, 3),
        "block_write_mb": round(write_b / _MB, 3),
    }
