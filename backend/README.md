# Cloud OS — Backend (FastAPI + PostgreSQL + Docker)

## Phase 2 — FastAPI, PostgreSQL, SQLAlchemy
REST CRUD for virtual machines and tasks, validated with Pydantic, persisted with SQLAlchemy.

## Phase 3 — Docker SDK
VMs are real Docker containers created through the Docker SDK for Python with enforced
CPU (`nano_cpus`) and memory (`mem_limit`) limits, a persistent volume mounted at `/data`,
container lifecycle endpoints, and database ⇄ Docker status synchronisation.
Requested storage (GB) is stored and displayed as *requested*; the local engine does not
enforce a hard volume quota, so it is never presented as enforced.

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then edit DATABASE_URL / DOCKER_HOST
createdb cloud_platform     # or use an existing PostgreSQL database
uvicorn app.main:app --reload --port 8000
```

Tables are created automatically on startup.

Docs: http://localhost:8000/docs · http://localhost:8000/redoc

## Environment

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string |
| `DOCKER_HOST` | `unix:///var/run/docker.sock` or `npipe:////./pipe/docker_engine` (Windows) |
| `DOCKER_ENABLED` | `false` to run Phase 2 only (database records, no containers) |
| `VM_BASE_IMAGE` | Base image, default `ubuntu:22.04` (pulled automatically) |
| `CORS_ORIGINS` | Comma-separated frontend origins |

## API

| Method | Path |
| --- | --- |
| GET | `/api/health` |
| GET | `/api/vms` |
| POST | `/api/vms` |
| GET | `/api/vms/{id}` |
| GET | `/api/vms/{id}/stats` |
| DELETE | `/api/vms/{id}` |
| POST | `/api/vms/{id}/start` |
| POST | `/api/vms/{id}/stop` |
| POST | `/api/vms/{id}/restart` |
| GET | `/api/tasks` |
| POST | `/api/tasks` |
| GET | `/api/tasks/{id}` |
| DELETE | `/api/tasks/{id}` |

## Safety
Containers run unprivileged (`cap_drop: ALL`, `no-new-privileges`), on the default bridge
network, with sanitised generated names (`cloudos-vm-{name}-{id}`). The Docker socket is
never mounted into user containers and the frontend never talks to Docker directly.
