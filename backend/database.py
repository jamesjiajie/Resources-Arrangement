import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "resources.db"


def today_iso() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def row_to_dict(row):
    return dict(row) if row else None


def fetch_all(conn: sqlite3.Connection, sql: str, params=()):
    return [row_to_dict(row) for row in conn.execute(sql, params).fetchall()]


@contextmanager
def get_db():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT '',
                team TEXT NOT NULL DEFAULT '',
                capacity_hours_week REAL NOT NULL DEFAULT 40,
                status TEXT NOT NULL DEFAULT 'available',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                priority TEXT NOT NULL DEFAULT 'medium',
                start_date TEXT,
                end_date TEXT,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                task_name TEXT NOT NULL,
                allocation_percent REAL NOT NULL DEFAULT 50,
                start_date TEXT NOT NULL,
                end_date TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                priority TEXT NOT NULL DEFAULT 'medium',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                sheet_name TEXT NOT NULL,
                resource_month TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_members INTEGER NOT NULL DEFAULT 0,
                reused_members INTEGER NOT NULL DEFAULT 0,
                created_projects INTEGER NOT NULL DEFAULT 0,
                reused_projects INTEGER NOT NULL DEFAULT 0,
                created_assignments INTEGER NOT NULL DEFAULT 0,
                skipped_assignments INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                action TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        ensure_column(conn, "assignments", "import_batch_id", "INTEGER")
        ensure_column(conn, "assignments", "source_key", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "assignments", "source_type", "TEXT NOT NULL DEFAULT 'manual'")


def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str):
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def seed_data(conn: sqlite3.Connection):
    timestamp = now_iso()
    members = [
        ("陈安", "后端工程师", "平台组", 40, "available", "熟悉 API 与数据建模"),
        ("李敏", "前端工程师", "体验组", 36, "available", "Vue 与交互实现"),
        ("王越", "测试工程师", "质量组", 32, "busy", "自动化测试和验收"),
        ("赵宁", "项目经理", "交付组", 40, "available", "跨项目协调"),
    ]
    conn.executemany(
        """
        INSERT INTO members
        (name, role, team, capacity_hours_week, status, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(*row, timestamp, timestamp) for row in members],
    )

    projects = [
        ("资源排期系统", "RA", "赵宁", "active", "high", "2026-05-01", "2026-06-30", "V2 内部资源工作台"),
        ("客户门户改版", "CP", "赵宁", "active", "medium", "2026-04-15", "2026-07-15", "前后端协同"),
        ("数据同步服务", "DS", "陈安", "planning", "medium", "2026-06-01", None, "等待接口确认"),
    ]
    conn.executemany(
        """
        INSERT INTO projects
        (name, code, owner, status, priority, start_date, end_date, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(*row, timestamp, timestamp) for row in projects],
    )

    assignments = [
        (1, 1, "FastAPI 服务与资源模型", 60, "2026-05-18", "2026-06-10", "active", "high", ""),
        (2, 1, "Vue 工作台体验升级", 55, "2026-05-18", "2026-06-05", "active", "high", ""),
        (3, 2, "回归测试计划", 40, "2026-05-20", "2026-06-20", "active", "medium", ""),
        (4, 1, "需求梳理与交付节奏", 25, "2026-05-18", "2026-06-30", "active", "medium", ""),
        (1, 3, "同步服务技术预研", 25, "2026-06-01", None, "planned", "medium", ""),
    ]
    conn.executemany(
        """
        INSERT INTO assignments
        (member_id, project_id, task_name, allocation_percent, start_date, end_date, status, priority, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(*row, timestamp, timestamp) for row in assignments],
    )
    conn.execute(
        """
        INSERT INTO activity_log (entity_type, entity_id, action, summary, created_at)
        VALUES ('system', NULL, 'seed', '初始化 V2 示例数据', ?)
        """,
        (timestamp,),
    )


def log_activity(conn: sqlite3.Connection, entity_type: str, entity_id, action: str, summary: str):
    conn.execute(
        """
        INSERT INTO activity_log (entity_type, entity_id, action, summary, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (entity_type, entity_id, action, summary, now_iso()),
    )
