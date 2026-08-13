import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    cpu_required: int = Field(gt=0, le=16)
    ram_required: int = Field(gt=0, le=32768, description="Memory in MB")
    assigned_vm_id: uuid.UUID | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Task name cannot be empty")
        return v


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    cpu_required: int
    ram_required: int
    status: str
    progress: int
    execution_time: float | None = None
    assigned_vm_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
