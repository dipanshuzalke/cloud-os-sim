import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VMMetric(Base):
    """One second-resolution sample of `docker stats` for a VM container."""

    __tablename__ = "vm_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vms.id", ondelete="CASCADE"), index=True
    )
    container_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_usage_mb: Mapped[float] = mapped_column(Float, default=0.0)
    memory_limit_mb: Mapped[float] = mapped_column(Float, default=0.0)
    memory_percent: Mapped[float] = mapped_column(Float, default=0.0)

    network_rx_mb: Mapped[float] = mapped_column(Float, default=0.0)
    network_tx_mb: Mapped[float] = mapped_column(Float, default=0.0)
    network_rx_rate_kbps: Mapped[float] = mapped_column(Float, default=0.0)
    network_tx_rate_kbps: Mapped[float] = mapped_column(Float, default=0.0)

    block_read_mb: Mapped[float] = mapped_column(Float, default=0.0)
    block_write_mb: Mapped[float] = mapped_column(Float, default=0.0)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


Index("ix_vm_metrics_vm_recorded", VMMetric.vm_id, VMMetric.recorded_at.desc())
