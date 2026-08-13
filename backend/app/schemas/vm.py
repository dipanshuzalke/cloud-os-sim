import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VMCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    cpu: int = Field(gt=0, le=16)
    ram: int = Field(gt=0, le=32768, description="Memory in MB")
    storage: int = Field(gt=0, le=1024, description="Requested storage in GB")

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("VM name cannot be empty")
        return v


class VMRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    cpu: int
    ram: int
    storage: int
    status: str
    image: str | None = None
    region: str | None = None
    container_id: str | None = None
    container_name: str | None = None
    volume_name: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class VMStats(BaseModel):
    container_id: str | None = None
    container_name: str | None = None
    container_status: str | None = None
    cpu_limit: float | None = None
    memory_limit_mb: int | None = None
    cpu_percent: float | None = None
    memory_usage_mb: float | None = None
