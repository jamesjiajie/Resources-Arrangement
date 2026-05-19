import sqlite3

from .database import fetch_all, log_activity, now_iso, today_iso
from .schemas import AssignmentIn, MemberIn, ProjectIn


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
        (member_id, project_id, task_name, allocation_percent, start_date, end_date, status, priority, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["member_id"],
            data["project_id"],
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


def update_assignment(conn: sqlite3.Connection, assignment_id: int, payload: AssignmentIn):
    data = payload.model_dump()
    cur = conn.execute(
        """
        UPDATE assignments
        SET member_id = ?, project_id = ?, task_name = ?, allocation_percent = ?,
            start_date = ?, end_date = ?, status = ?, priority = ?, notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            data["member_id"],
            data["project_id"],
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
