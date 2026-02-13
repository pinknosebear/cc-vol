from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_db_connection, create_tables
from app.routes.volunteers import router as volunteers_router

app = FastAPI(title="cc-vol", description="Volunteer Scheduling System")
app.include_router(volunteers_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
