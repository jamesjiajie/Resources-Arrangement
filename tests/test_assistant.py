import io
import json
import sqlite3
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from backend.assistant import _safe_text, answer_stream, capacity_summary, search_records


class AssistantDataTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE members (id INTEGER PRIMARY KEY, name TEXT, role TEXT, team TEXT, status TEXT, notes TEXT);
            CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE assignments (id INTEGER PRIMARY KEY, member_id INTEGER, project_id INTEGER, task_name TEXT,
                allocation_percent REAL, start_date TEXT, end_date TEXT, status TEXT, archived_month TEXT);
            CREATE TABLE long_term_tasks (id INTEGER PRIMARY KEY, title TEXT);
            CREATE TABLE import_batches (id INTEGER PRIMARY KEY, filename TEXT);
            CREATE TABLE activity_log (id INTEGER PRIMARY KEY, summary TEXT);
            CREATE TABLE freeform_sandboxes (id TEXT PRIMARY KEY, title TEXT, document TEXT, updated_at TEXT);
            INSERT INTO members VALUES (1, '林佳', '工程师', '平台', 'available', '熟悉 API');
            INSERT INTO members VALUES (2, '王宁', '工程师', '平台', 'away', '休假待确认');
            INSERT INTO projects VALUES (1, '新平台');
            INSERT INTO assignments VALUES (1, 1, 1, '接口', 80, '2026-10-01', NULL, 'active', NULL);
            INSERT INTO assignments VALUES (2, 1, 1, '旧任务', 50, '2026-10-01', NULL, 'active', '2026-10');
            INSERT INTO assignments VALUES (3, 2, 1, '已完成', 60, '2026-10-01', NULL, 'done', NULL);
            INSERT INTO freeform_sandboxes VALUES ('a', '设想方案', '{"nodes":[{"text":"备选人员"}]}', '2026-09-01');
        """)

    def tearDown(self):
        self.conn.close()

    def test_capacity_excludes_archived_and_done_and_reserves_ten_percent(self):
        result = capacity_summary(self.conn, "2026-10", [])
        self.assertEqual(result["people"][0]["name"], "林佳")
        self.assertEqual(result["people"][0]["monthly_average_book_percent"], 20)
        self.assertEqual(result["people"][0]["monthly_average_recommended_percent"], 10)
        self.assertTrue(result["people"][1]["temporarily_away"])
        self.assertEqual(result["people"][1]["monthly_average_recommended_percent"], 90)

    def test_search_includes_archived_and_sandbox_notes(self):
        self.assertEqual(search_records(self.conn, "旧任务", [])["matched"], 1)
        self.assertEqual(search_records(self.conn, "备选人员", [])["results"][0]["kind"], "sandbox")

    def test_credentials_are_removed_before_model_context(self):
        self.assertNotIn("sensitive-value", _safe_text("API key: sensitive-value"))
        self.assertNotIn("sensitive-value", _safe_text("Bearer sensitive-value"))

    def test_tool_answer_stream_carries_real_source(self):
        calls = [
            io.BytesIO(json.dumps({"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call_1", "type": "function", "function": {"name": "capacity_summary", "arguments": '{"month":"2026-10"}'},
            }]}}]}).encode()),
            io.BytesIO(json.dumps({"choices": [{"message": {"role": "assistant", "content": "ready"}}]}).encode()),
            io.BytesIO(b'data: {"choices":[{"delta":{"content":"Lin has 10% [S1]."}}]}\n\ndata: [DONE]\n\n'),
        ]
        with patch("backend.assistant._call_agnes", side_effect=calls):
            events = list(answer_stream(lambda: nullcontext(self.conn), [], "下个月谁有余量？", "总览"))
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(events[-1]["sources"][0]["ref"], "S1")


if __name__ == "__main__":
    unittest.main()
