import sqlite3

from .database import fetch_all, log_activity, now_iso, today_iso
from .schemas import AssignmentIn, LongTermTaskIn, MemberIn, ProjectIn


def is_current_assignment(assignment, current_date: str) -> bool:
    if assignment["status"] not in ("active", "planned", "blocked"):
        return False
    if assignment["start_date"] > current_date:
        return assignment["status"] in ("active", "blocked")
    if assignment["end_date"] and assignment["end_date"] < current_date:
        return False
    return True


def list_assignments(conn: sqlite3.Connection):
    return fetch_all(
        conn,
        """
        SELECT
            a.*,
            m.name AS member_name,
            m.role AS member_role,
            m.team AS member_team,
            m.capacity_hours_week,
            p.name AS project_name,
            p.code AS project_code,
            p.owner AS project_owner
        FROM assignments a
        JOIN members m ON m.id = a.member_id
        JOIN projects p ON p.id = a.project_id
        ORDER BY
            CASE a.status WHEN 'blocked' THEN 0 WHEN 'active' THEN 1 WHEN 'planned' THEN 2 ELSE 3 END,
            COALESCE(a.end_date, '9999-12-31'),
            CASE a.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END
        """,
    )


def build_overview(conn: sqlite3.Connection, current_date: str = None):
    selected_date = current_date or today_iso()
    members = fetch_all(conn, "SELECT * FROM members ORDER BY name")
    projects = fetch_all(
        conn,
        """
        SELECT * FROM projects
        ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, name
        """,
    )
    assignments = list_assignments(conn)

    member_load = {}
    for member in members:
        member_load[member["id"]] = {
            "member_id": member["id"],
            "name": member["name"],
            "role": member["role"],
            "team": member["team"],
            "capacity_hours_week": member["capacity_hours_week"],
            "allocated_percent": 0,
            "allocated_hours": 0,
            "active_count": 0,
            "blocked_count": 0,
            "project_names": [],
            "risk": "normal",
        }

    project_load = {}
    for project in projects:
        project_load[project["id"]] = {
            "project_id": project["id"],
            "name": project["name"],
            "code": project["code"],
            "allocated_percent": 0,
            "people_count": 0,
            "status": project["status"],
            "priority": project["priority"],
        }

    for assignment in assignments:
        if not is_current_assignment(assignment, selected_date):
            continue
        load = member_load.get(assignment["member_id"])
        if load:
            load["allocated_percent"] += assignment["allocation_percent"]
            load["active_count"] += 1
            if assignment["status"] == "blocked":
                load["blocked_count"] += 1
            if assignment["project_name"] not in load["project_names"]:
                load["project_names"].append(assignment["project_name"])
        project = project_load.get(assignment["project_id"])
        if project:
            project["allocated_percent"] += assignment["allocation_percent"]
            project["people_count"] += 1

    for load in member_load.values():
        load["allocated_hours"] = round(load["capacity_hours_week"] * load["allocated_percent"] / 100, 1)
        if load["blocked_count"]:
            load["risk"] = "blocked"
        elif load["allocated_percent"] >= 110:
            load["risk"] = "overloaded"
        elif load["allocated_percent"] >= 90:
            load["risk"] = "tight"
        elif load["allocated_percent"] <= 35:
            load["risk"] = "underused"

    overdue_assignments = [
        item
        for item in assignments
        if item["status"] in ("active", "blocked") and item["end_date"] and item["end_date"] < selected_date
    ]
    active_projects = [project for project in projects if project["status"] == "active"]
    active_assignments = [item for item in assignments if item["status"] == "active"]
    blocked_assignments = [item for item in assignments if item["status"] == "blocked"]
    activity = fetch_all(conn, "SELECT * FROM activity_log ORDER BY id DESC LIMIT 20")

    total_capacity = sum(item["capacity_hours_week"] for item in members)
    total_allocated_hours = sum(item["allocated_hours"] for item in member_load.values())
    average_load = round((total_allocated_hours / total_capacity) * 100, 1) if total_capacity else 0

    return {
        "current_date": selected_date,
        "members": members,
        "projects": projects,
        "assignments": assignments,
        "member_load": list(member_load.values()),
        "project_load": list(project_load.values()),
        "activity": activity,
        "stats": {
            "member_count": len(members),
            "active_project_count": len(active_projects),
            "active_assignment_count": len(active_assignments),
            "blocked_assignment_count": len(blocked_assignments),
            "overdue_assignment_count": len(overdue_assignments),
            "average_load": average_load,
            "total_capacity_hours": total_capacity,
            "allocated_hours": round(total_allocated_hours, 1),
        },
    }


def create_member(conn: sqlite3.Connection, payload: MemberIn):
    data = payload.model_dump()
    timestamp = now_iso()
    cur = conn.execute(
        """
        INSERT INTO members
        (name, role, team, capacity_hours_week, status, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"].strip(),
            data["role"].strip(),
            data["team"].strip(),
            data["capacity_hours_week"],
            data["status"],
            data["notes"].strip(),
            timestamp,
            timestamp,
        ),
    )
    log_activity(conn, "member", cur.lastrowid, "create", "新增同事: " + data["name"].strip())
    return cur.lastrowid


def create_project(conn: sqlite3.Connection, payload: ProjectIn):
    data = payload.model_dump()
    timestamp = now_iso()
    cur = conn.execute(
        """
        INSERT INTO projects
        (name, code, owner, status, priority, start_date, end_date, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"].strip(),
            data["code"].strip(),
            data["owner"].strip(),
            data["status"],
            data["priority"],
            data["start_date"] or None,
            data["end_date"] or None,
            data["notes"].strip(),
            timestamp,
            timestamp,
        ),
    )
    log_activity(conn, "project", cur.lastrowid, "create", "新增项目: " + data["name"].strip())
    return cur.lastrowid


def create_assignment(conn: sqlite3.Connection, payload: AssignmentIn):
    data = payload.model_dump()
    timestamp = now_iso()
    cur = conn.execute(
        """
        INSERT INTO assignments
        (member_id, project_id, project_pm_item, task_name, allocation_percent, start_date, end_date, status, priority, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["member_id"],
            data["project_id"],
            data["project_pm_item"].strip(),
            data["task_name"].strip(),
            data["allocation_percent"],
            data["start_date"],
            data["end_date"] or None,
            data["status"],
            data["priority"],
            data["notes"].strip(),
            timestamp,
            timestamp,
        ),
    )
    log_activity(conn, "assignment", cur.lastrowid, "create", "新增安排: " + data["task_name"].strip())
    return cur.lastrowid


def find_by_name(conn: sqlite3.Connection, table_name: str, name: str):
    return conn.execute(
        f"SELECT * FROM {table_name} WHERE lower(trim(name)) = lower(trim(?)) LIMIT 1",
        (name,),
    ).fetchone()


def update_member_from_import(conn: sqlite3.Connection, member_id: int, member: dict):
    existing = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    role = existing["role"] or member["role"]
    team = existing["team"] or member["team"]
    notes = existing["notes"]
    if member["notes"] and member["notes"] not in notes:
        notes = (notes + "\n" if notes else "") + member["notes"]
    conn.execute(
        """
        UPDATE members
        SET role = ?, team = ?, status = ?, notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (role, team, member["status"], notes, now_iso(), member_id),
    )


def update_project_from_import(conn: sqlite3.Connection, project_id: int, project: dict):
    existing = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    owner = existing["owner"] or project["owner"]
    notes = existing["notes"]
    if project["notes"] and project["notes"] not in notes:
        notes = (notes + "\n" if notes else "") + project["notes"]
    conn.execute(
        """
        UPDATE projects
        SET owner = ?, start_date = COALESCE(start_date, ?), end_date = COALESCE(end_date, ?),
            notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (owner, project["start_date"], project["end_date"], notes, now_iso(), project_id),
    )


def create_import_batch(conn: sqlite3.Connection, preview: dict, mode: str, stats: dict):
    cur = conn.execute(
        """
        INSERT INTO import_batches
        (filename, sheet_name, resource_month, file_hash, mode, created_members, reused_members,
         created_projects, reused_projects, created_assignments, skipped_assignments, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            preview["filename"],
            preview["sheet_name"],
            preview["resource_month"],
            preview["file_hash"],
            mode,
            stats["created_members"],
            stats["reused_members"],
            stats["created_projects"],
            stats["reused_projects"],
            stats["created_assignments"],
            stats["skipped_assignments"],
            now_iso(),
        ),
    )
    return cur.lastrowid


def list_import_batches(conn: sqlite3.Connection):
    return fetch_all(conn, "SELECT * FROM import_batches ORDER BY id DESC LIMIT 30")


def list_long_term_tasks(conn: sqlite3.Connection):
    return fetch_all(
        conn,
        """
        SELECT * FROM long_term_tasks
        ORDER BY
            CASE status
                WHEN 'blocked' THEN 0
                WHEN 'active' THEN 1
                WHEN 'planned' THEN 2
                WHEN 'done' THEN 3
                ELSE 4
            END,
            COALESCE(target_date, '9999-12-31'),
            CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
            updated_at DESC
        """,
    )


def create_long_term_task(conn: sqlite3.Connection, payload: LongTermTaskIn):
    data = payload.model_dump()
    timestamp = now_iso()
    cur = conn.execute(
        """
        INSERT INTO long_term_tasks
        (title, owner, category, status, priority, progress, start_date, target_date, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["title"].strip(),
            data["owner"].strip(),
            data["category"].strip(),
            data["status"],
            data["priority"],
            data["progress"],
            data["start_date"] or None,
            data["target_date"] or None,
            data["notes"].strip(),
            timestamp,
            timestamp,
        ),
    )
    log_activity(conn, "long_term_task", cur.lastrowid, "create", "新增长期任务: " + data["title"].strip())
    return cur.lastrowid


def update_long_term_task(conn: sqlite3.Connection, task_id: int, payload: LongTermTaskIn):
    data = payload.model_dump()
    cur = conn.execute(
        """
        UPDATE long_term_tasks
        SET title = ?, owner = ?, category = ?, status = ?, priority = ?, progress = ?,
            start_date = ?, target_date = ?, notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            data["title"].strip(),
            data["owner"].strip(),
            data["category"].strip(),
            data["status"],
            data["priority"],
            data["progress"],
            data["start_date"] or None,
            data["target_date"] or None,
            data["notes"].strip(),
            now_iso(),
            task_id,
        ),
    )
    if cur.rowcount == 0:
        return False
    log_activity(conn, "long_term_task", task_id, "update", "更新长期任务: " + data["title"].strip())
    return True


def apply_excel_import(conn: sqlite3.Connection, preview: dict, mode: str):
    if mode not in ("append", "replace_month", "update_catalog"):
        raise ValueError("未知导入模式")
    if not preview.get("assignments"):
        raise ValueError("没有识别到可导入的 FTE 安排，已取消导入以保护现有月份数据")

    if mode in ("replace_month", "update_catalog"):
        conn.execute(
            """
            DELETE FROM assignments
            WHERE source_type = 'excel'
              AND import_batch_id IN (
                SELECT id FROM import_batches WHERE resource_month = ?
              )
            """,
            (preview["resource_month"],),
        )

    stats = {
        "created_members": 0,
        "reused_members": 0,
        "created_projects": 0,
        "reused_projects": 0,
        "created_assignments": 0,
        "skipped_assignments": 0,
    }

    member_ids = {}
    for member in preview["members"]:
        existing = find_by_name(conn, "members", member["name"])
        if existing:
            member_ids[member["name"]] = existing["id"]
            stats["reused_members"] += 1
            if mode == "update_catalog":
                update_member_from_import(conn, existing["id"], member)
            continue
        payload = MemberIn(**{key: member[key] for key in ("name", "role", "team", "capacity_hours_week", "status", "notes")})
        member_ids[member["name"]] = create_member(conn, payload)
        stats["created_members"] += 1

    project_ids = {}
    for project in preview["projects"]:
        existing = find_by_name(conn, "projects", project["name"])
        if existing:
            project_ids[project["name"]] = existing["id"]
            stats["reused_projects"] += 1
            if mode == "update_catalog":
                update_project_from_import(conn, existing["id"], project)
            continue
        payload = ProjectIn(
            **{
                key: project[key]
                for key in ("name", "code", "owner", "status", "priority", "start_date", "end_date", "notes")
            }
        )
        project_ids[project["name"]] = create_project(conn, payload)
        stats["created_projects"] += 1

    batch_id = create_import_batch(conn, preview, mode, stats)
    timestamp = now_iso()

    for assignment in preview["assignments"]:
        member_id = member_ids.get(assignment["member_name"])
        project_id = project_ids.get(assignment["project_name"])
        if not member_id or not project_id:
            stats["skipped_assignments"] += 1
            continue
        conn.execute(
            """
            INSERT INTO assignments
            (member_id, project_id, project_pm_item, task_name, allocation_percent, start_date, end_date,
             status, priority, notes, created_at, updated_at, import_batch_id, source_key, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'excel')
            """,
            (
                member_id,
                project_id,
                assignment["project_pm_item"],
                assignment["task_name"],
                assignment["allocation_percent"],
                assignment["start_date"],
                assignment["end_date"],
                assignment["status"],
                assignment["priority"],
                assignment["notes"],
                timestamp,
                timestamp,
                batch_id,
                assignment["source_key"],
            ),
        )
        stats["created_assignments"] += 1

    conn.execute(
        """
        UPDATE import_batches
        SET created_assignments = ?, skipped_assignments = ?
        WHERE id = ?
        """,
        (stats["created_assignments"], stats["skipped_assignments"], batch_id),
    )
    log_activity(
        conn,
        "import",
        batch_id,
        "excel",
        f"导入 Excel: {preview['filename']} / {preview['sheet_name']}，生成 {stats['created_assignments']} 条安排",
    )
    return {"batch_id": batch_id, **stats}


def update_assignment(conn: sqlite3.Connection, assignment_id: int, payload: AssignmentIn):
    data = payload.model_dump()
    cur = conn.execute(
        """
        UPDATE assignments
        SET member_id = ?, project_id = ?, project_pm_item = ?, task_name = ?, allocation_percent = ?,
            start_date = ?, end_date = ?, status = ?, priority = ?, notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            data["member_id"],
            data["project_id"],
            data["project_pm_item"].strip(),
            data["task_name"].strip(),
            data["allocation_percent"],
            data["start_date"],
            data["end_date"] or None,
            data["status"],
            data["priority"],
            data["notes"].strip(),
            now_iso(),
            assignment_id,
        ),
    )
    if cur.rowcount == 0:
        return False
    log_activity(conn, "assignment", assignment_id, "update", "更新安排: " + data["task_name"].strip())
    return True


def delete_entity(conn: sqlite3.Connection, table_name: str, entity_type: str, entity_id: int):
    cur = conn.execute(f"DELETE FROM {table_name} WHERE id = ?", (entity_id,))
    if cur.rowcount == 0:
        return False
    log_activity(conn, entity_type, entity_id, "delete", f"删除 {entity_type} #{entity_id}")
    return True
