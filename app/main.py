from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_db_connection, create_tables
from app.routes.coordinator import router as coordinator_router
from app.routes.shifts import router as shifts_router
from app.routes.signups import router as signups_router
from app.routes.volunteers import router as volunteers_router
from app.routes.wa_incoming import router as wa_incoming_router

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

DB_PATH = "cc-vol.db"


@app.on_event("startup")
def startup():
    conn = get_db_connection(DB_PATH)
    create_tables(conn)
    app.state.db = conn


@app.on_event("shutdown")
def shutdown():
    app.state.db.close()


def get_db(request: Request):
    """Dependency helper for route handlers to get the DB connection."""
    return request.app.state.db


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
