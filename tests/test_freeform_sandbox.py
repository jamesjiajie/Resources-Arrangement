import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from backend import database
from backend.main import SandboxDocument, create_freeform_sandbox, delete_freeform_sandbox, get_freeform_sandbox, list_freeform_sandboxes, on_startup, save_freeform_sandbox


class FreeformSandboxTest(unittest.TestCase):
    def test_document_lifecycle_and_stale_save(self):
        original_path = database.DB_PATH
        with tempfile.TemporaryDirectory() as directory:
            database.DB_PATH = Path(directory) / "resources.db"
            try:
                on_startup()
                payload = {
                    "title": "试验方案",
                    "nodes": [{"id": "p1", "type": "person", "x": 20, "y": 30}],
                    "edges": [],
                    "viewport": {"x": 0, "y": 0, "zoom": 1},
                    "revision": 0,
                }
                created = create_freeform_sandbox(SandboxDocument(**payload))
                sandbox_id = created["id"]
                self.assertEqual(get_freeform_sandbox(sandbox_id)["nodes"], payload["nodes"])
                self.assertEqual(len(list_freeform_sandboxes()["sandboxes"]), 1)

                changed = SandboxDocument(**{**payload, "title": "调整后", "revision": 1})
                self.assertEqual(save_freeform_sandbox(sandbox_id, changed)["revision"], 2)
                with self.assertRaises(HTTPException) as stale:
                    save_freeform_sandbox(sandbox_id, changed)
                self.assertEqual(stale.exception.status_code, 409)
                self.assertEqual(get_freeform_sandbox(sandbox_id)["title"], "调整后")

                self.assertEqual(delete_freeform_sandbox(sandbox_id), {"ok": True})
                with self.assertRaises(HTTPException) as missing:
                    get_freeform_sandbox(sandbox_id)
                self.assertEqual(missing.exception.status_code, 404)
            finally:
                database.DB_PATH = original_path


if __name__ == "__main__":
    unittest.main()
