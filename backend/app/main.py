import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import tasks, vms
from app.core.config import settings
from app.core.database import Base, engine
from app.models import Task, User, VM, Workspace  # noqa: F401 - register metadata
from app.services import docker_service

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Cloud OS API",
    description="Virtual Cloud Infrastructure Simulator — FastAPI + PostgreSQL + Docker",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_origin_regex=r"https?://.*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vms.router)
app.include_router(tasks.router)


@app.get("/api/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "docker": docker_service.docker_available(),
        "image": settings.vm_base_image,
    }
