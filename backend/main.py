import sqlite3
import json
import os
from uuid import uuid4
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .database import BASE_DIR, get_db, init_db
from .database import now_iso
from .assistant import answer_stream, get_record
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


env_file = BASE_DIR / ".env"
if env_file.exists() and not os.environ.get("AGNES_API_KEY"):
    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "AGNES_API_KEY":
            os.environ["AGNES_API_KEY"] = value.strip().strip("\"'")
            break


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


@app.get("/api/assistant/conversations")
def assistant_conversations():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM assistant_conversations ORDER BY updated_at DESC").fetchall()
    return {"configured": bool(os.environ.get("AGNES_API_KEY", "").strip()), "conversations": [dict(row) for row in rows]}


@app.get("/api/assistant/sources/{kind}/{record_id}")
def assistant_source(kind: str, record_id: str):
    with get_db() as conn:
        result = get_record(conn, kind, record_id, [])
    if "error" in result:
        raise HTTPException(status_code=404, detail="资料不存在")
    return {"record": json.loads(result["record"]) if not result["truncated"] else result["record"], "truncated": result["truncated"]}


@app.post("/api/assistant/conversations", status_code=201)
def create_assistant_conversation():
    conversation_id = str(uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO assistant_conversations VALUES (?, ?, ?, ?)",
                     (conversation_id, "新对话", now_iso(), now_iso()))
    return {"id": conversation_id}


@app.get("/api/assistant/conversations/{conversation_id}")
def assistant_conversation(conversation_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM assistant_conversations WHERE id = ?", (conversation_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="对话不存在")
        messages = conn.execute("SELECT role, content, sources, created_at FROM assistant_messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)).fetchall()
    return {"conversation": dict(row), "messages": [{**dict(item), "sources": json.loads(item["sources"])} for item in messages]}


@app.delete("/api/assistant/conversations/{conversation_id}")
def delete_assistant_conversation(conversation_id: str):
    with get_db() as conn:
        deleted = conn.execute("DELETE FROM assistant_conversations WHERE id = ?", (conversation_id,))
    if not deleted.rowcount:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"ok": True}


class AssistantQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    page_context: str = Field(default="总览", max_length=200)


@app.post("/api/assistant/conversations/{conversation_id}/messages")
def ask_assistant(conversation_id: str, payload: AssistantQuestion):
    if not os.environ.get("AGNES_API_KEY", "").strip():
        raise HTTPException(status_code=503, detail="尚未配置 AGNES_API_KEY；请在启动 portal 的服务端环境中设置。")
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="请输入问题")
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM assistant_conversations WHERE id = ?", (conversation_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="对话不存在")
        history = [dict(item) for item in conn.execute(
            "SELECT role, content FROM assistant_messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 8", (conversation_id,)).fetchall()][::-1]
        last = conn.execute("SELECT role, content FROM assistant_messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 1", (conversation_id,)).fetchone()
        if last is None or last["role"] != "user" or last["content"] != question:
            conn.execute("INSERT INTO assistant_messages (conversation_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
                         (conversation_id, question, now_iso()))
        conn.execute("UPDATE assistant_conversations SET title = CASE WHEN title = '新对话' THEN ? ELSE title END, updated_at = ? WHERE id = ?",
                     (question[:36], now_iso(), conversation_id))

    def events():
        try:
            for event in answer_stream(get_db, history, question, payload.page_context):
                if event["type"] == "done":
                    with get_db() as conn:
                        conn.execute("INSERT INTO assistant_messages (conversation_id, role, content, sources, created_at) VALUES (?, 'assistant', ?, ?, ?)",
                                     (conversation_id, event["text"], json.dumps(event["sources"], ensure_ascii=False), now_iso()))
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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
