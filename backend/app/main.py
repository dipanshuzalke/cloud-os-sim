import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import metrics, tasks, vms
from app.core.config import settings
from app.core.database import Base, engine
from app.core.realtime import socket_app
from app.models import Task, User, VM, Workspace  # noqa: F401 - register metadata
from app.services import docker_service, monitor_service

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    monitor_service.start()
    try:
        yield
    finally:
        await monitor_service.stop()


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
app.include_router(metrics.router)

# Socket.IO endpoint for live `docker stats` streaming (Phase 4)
app.mount("/socket.io", socket_app)


@app.get("/api/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "docker": docker_service.docker_available(),
        "image": settings.vm_base_image,
        "realtime": "socket.io",
    }
