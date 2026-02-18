import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import get_db_connection, create_tables
from app.routes.coordinator import router as coordinator_router
from app.routes.shifts import router as shifts_router
from app.routes.signups import router as signups_router
from app.routes.volunteers import router as volunteers_router
from app.routes.wa_incoming import router as wa_incoming_router
from app.scheduler import start_scheduler, shutdown_scheduler

app = FastAPI(title="cc-vol", description="Volunteer Scheduling System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(coordinator_router)
app.include_router(shifts_router)
app.include_router(signups_router)
app.include_router(volunteers_router)
app.include_router(wa_incoming_router)

@app.on_event("startup")
def startup():
    db_path = os.getenv("DB_PATH", "cc-vol.db")
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection(db_path)
    create_tables(conn)
    app.state.db = conn
    app.state.scheduler = start_scheduler()


@app.on_event("shutdown")
def shutdown():
    app.state.db.close()
    shutdown_scheduler(app.state.scheduler)


def get_db(request: Request):
    """Dependency helper for route handlers to get the DB connection."""
    return request.app.state.db


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "chat.html")


@app.get("/dashboard")
def dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/volunteer")
def volunteer():
    return FileResponse(STATIC_DIR / "volunteer.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
