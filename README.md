# Welcome to your Lovable project

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Open your project in the [Lovable editor](https://lovable.dev) and keep building.

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: connect the project to GitHub and every change made in Lovable is committed straight to your repository.
- **Full ownership**: this code is yours. Push to your repository and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```

## Built with

- TanStack Start
- TypeScript
- React
- Tailwind CSS

## Phase 2 — Backend & Database
FastAPI + PostgreSQL + SQLAlchemy REST API for VM and task CRUD. See `backend/README.md`.

## Phase 3 — Docker Integration
The backend creates real Docker containers through the Docker SDK for Python with enforced
CPU/RAM limits, lifecycle control (start / stop / restart / delete) and Docker ⇄ database
status synchronisation.

### Running locally
1. `cd backend && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --reload --port 8000`
2. In the project root: `cp .env.example .env` (set `VITE_API_URL=http://localhost:8000`) and `npm run dev`
