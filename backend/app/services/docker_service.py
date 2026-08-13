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
