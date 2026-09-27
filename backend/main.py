import sqlite3
import json
from uuid import uuid4
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import BASE_DIR, get_db, init_db
from .database import now_iso
from .excel_import import parse_resource_workbook
from .sharepoint import preview_excel
from .schemas import AssignmentIn, LongTermTaskIn, MemberIn, ProjectIn
from pydantic import BaseModel, Field
from .services import (
    apply_excel_import,
    build_overview,
    create_assignment,
    create_long_term_task,
    create_member,
    create_project,
    delete_entity,
    archive_month,
    list_archived_assignments,
    list_import_batches,
    list_long_term_tasks,
    update_assignment,
    update_long_term_task,
    restore_month,
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


@app.get("/api/imports")
def imports():
    with get_db() as conn:
        return {"imports": list_import_batches(conn)}


@app.get("/api/assignments/archive")
def archived_assignments():
    with get_db() as conn:
        return {"assignments": list_archived_assignments(conn)}


@app.post("/api/assignments/archive/{month}")
def archive_assignments(month: str):
    try:
        with get_db() as conn:
            return {"ok": True, "count": archive_month(conn, month)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/assignments/archive/{month}/restore")
def restore_archived_assignments(month: str):
    try:
        with get_db() as conn:
            return {"ok": True, "count": restore_month(conn, month)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/tasks")
def tasks():
    with get_db() as conn:
        return {"tasks": list_long_term_tasks(conn)}


@app.post("/api/sharepoint/excel/preview")
async def preview_sharepoint_excel(request: Request):
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先连接 Microsoft 账号")
    access_token = authorization.removeprefix("Bearer ").strip()
    if not access_token:
        raise HTTPException(status_code=401, detail="请先连接 Microsoft 账号")
    payload = await request.json()
    share_url = str(payload.get("share_url", "")).strip()
    if not share_url:
        raise HTTPException(status_code=400, detail="请输入 SharePoint 分享链接")
    try:
        return preview_excel(share_url, access_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SharePoint 读取失败: {exc}")


@app.post("/api/imports/excel/preview")
async def preview_excel_import(request: Request):
    filename = unquote(request.headers.get("x-filename", "uploaded.xlsx"))
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="请上传 Excel 文件")
    try:
        return parse_resource_workbook(content, filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel 解析失败: {exc}")


@app.post("/api/imports/excel/apply")
async def apply_excel_import_route(request: Request, mode: str = "replace_month"):
    filename = unquote(request.headers.get("x-filename", "uploaded.xlsx"))
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="请上传 Excel 文件")
    try:
        preview = parse_resource_workbook(content, filename)
        with get_db() as conn:
            result = apply_excel_import(conn, preview, mode)
        return {"ok": True, "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel 导入失败: {exc}")


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


@app.post("/api/tasks", status_code=201)
def add_task(payload: LongTermTaskIn):
    try:
        with get_db() as conn:
            task_id = create_long_term_task(conn, payload)
        return {"id": task_id}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/api/tasks/{task_id}")
def edit_task(task_id: int, payload: LongTermTaskIn):
    try:
        with get_db() as conn:
            updated = update_long_term_task(conn, task_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="长期任务不存在")
        return {"ok": True}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: int):
    with get_db() as conn:
        deleted = delete_entity(conn, "long_term_tasks", "long_term_task", task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="长期任务不存在")
    return {"ok": True}


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


class SandboxDocument(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
    viewport: dict = Field(default_factory=lambda: {"x": 0, "y": 0, "zoom": 1})
    revision: int = 0


@app.get("/api/freeform-sandboxes")
def list_freeform_sandboxes():
    with get_db() as conn:
        return {"sandboxes": [dict(row) for row in conn.execute(
            "SELECT id, title, revision, updated_at FROM freeform_sandboxes ORDER BY updated_at DESC"
        ).fetchall()]}


@app.post("/api/freeform-sandboxes", status_code=201)
def create_freeform_sandbox(payload: SandboxDocument):
    sandbox_id = str(uuid4())
    document = payload.model_dump(exclude={"revision"})
    with get_db() as conn:
        conn.execute(
            "INSERT INTO freeform_sandboxes (id, title, document, updated_at) VALUES (?, ?, ?, ?)",
            (sandbox_id, payload.title, json.dumps(document, ensure_ascii=False), now_iso()),
        )
    return {"id": sandbox_id, "revision": 1}


@app.get("/api/freeform-sandboxes/{sandbox_id}")
def get_freeform_sandbox(sandbox_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT document, revision FROM freeform_sandboxes WHERE id = ?", (sandbox_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="沙盘不存在")
    return {**json.loads(row["document"]), "revision": row["revision"]}


@app.put("/api/freeform-sandboxes/{sandbox_id}")
def save_freeform_sandbox(sandbox_id: str, payload: SandboxDocument):
    document = payload.model_dump(exclude={"revision"})
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE freeform_sandboxes SET title = ?, document = ?, revision = revision + 1, updated_at = ? "
            "WHERE id = ? AND revision = ?",
            (payload.title, json.dumps(document, ensure_ascii=False), now_iso(), sandbox_id, payload.revision),
        )
        if not cursor.rowcount:
            exists = conn.execute("SELECT 1 FROM freeform_sandboxes WHERE id = ?", (sandbox_id,)).fetchone()
            raise HTTPException(status_code=409 if exists else 404, detail="沙盘已被其他窗口修改" if exists else "沙盘不存在")
    return {"revision": payload.revision + 1}


@app.delete("/api/freeform-sandboxes/{sandbox_id}")
def delete_freeform_sandbox(sandbox_id: str):
    with get_db() as conn:
        deleted = conn.execute("DELETE FROM freeform_sandboxes WHERE id = ?", (sandbox_id,))
    if not deleted.rowcount:
        raise HTTPException(status_code=404, detail="沙盘不存在")
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
