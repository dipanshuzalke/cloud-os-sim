"""Socket.IO server used to push live resource metrics to the React client."""

from __future__ import annotations

import logging

import socketio

from app.core.config import settings

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origin_list or "*",
    logger=False,
    engineio_logger=False,
)

socket_app = socketio.ASGIApp(sio, socketio_path="")

EVENT_METRICS = "metrics"


@sio.event
async def connect(sid, _environ, _auth=None):
    logger.info("socket.io client connected: %s", sid)
    await sio.emit("connected", {"ok": True}, to=sid)


@sio.event
async def disconnect(sid):
    logger.info("socket.io client disconnected: %s", sid)


async def emit_metrics(payload: dict) -> None:
    await sio.emit(EVENT_METRICS, payload)
