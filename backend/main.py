import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import BASE_DIR, get_db, init_db
from .schemas import AssignmentIn, MemberIn, ProjectIn
from .services import (
    build_overview,
    create_assignment,
    create_member,
    create_project,
    delete_entity,
    update_assignment,
)


app = FastAPI(title="资源安排 API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"ok": True, "version": "2.0.0"}


@app.get("/api/overview")
def overview(date: Optional[str] = None):
    with get_db() as conn:
        return build_overview(conn, date)


@app.post("/api/members", status_code=201)
def add_member(payload: MemberIn):
    try:
        with get_db() as conn:
            entity_id = create_member(conn, payload)
        return {"id": entity_id}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/projects", status_code=201)
def add_project(payload: ProjectIn):
    try:
        with get_db() as conn:
            entity_id = create_project(conn, payload)
        return {"id": entity_id}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/assignments", status_code=201)
def add_assignment(payload: AssignmentIn):
    try:
        with get_db() as conn:
            entity_id = create_assignment(conn, payload)
        return {"id": entity_id}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/api/assignments/{assignment_id}")
def edit_assignment(assignment_id: int, payload: AssignmentIn):
    try:
        with get_db() as conn:
            updated = update_assignment(conn, assignment_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="安排不存在")
        return {"ok": True}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/{resource}/{entity_id}")
def remove_entity(resource: str, entity_id: int):
    table_map = {
        "members": ("members", "member"),
        "projects": ("projects", "project"),
        "assignments": ("assignments", "assignment"),
    }
    if resource not in table_map:
        raise HTTPException(status_code=404, detail="未知资源")
    table_name, entity_type = table_map[resource]
    with get_db() as conn:
        deleted = delete_entity(conn, table_name, entity_type, entity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}


dist_dir = BASE_DIR / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    index_file = dist_dir / "index.html"
    requested = dist_dir / full_path
    if dist_dir.exists() and requested.is_file():
        return FileResponse(requested)
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="前端尚未构建，请运行 npm run dev 或 npm run build")
