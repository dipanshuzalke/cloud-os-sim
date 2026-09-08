import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vm_id: uuid.UUID
    container_id: str | None = None
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    memory_percent: float
    network_rx_mb: float
    network_tx_mb: float
    network_rx_rate_kbps: float
    network_tx_rate_kbps: float
    block_read_mb: float
    block_write_mb: float
    recorded_at: datetime


class FleetSample(BaseModel):
    """Aggregated fleet-level point emitted every second over Socket.IO."""

    recorded_at: datetime
    running_vms: int
    cpu_percent: float
    memory_percent: float
    memory_usage_mb: float
    network_rx_rate_kbps: float
    network_tx_rate_kbps: float
