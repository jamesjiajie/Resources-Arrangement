import io
import sqlite3
import unittest
import zipfile
from xml.sax.saxutils import escape

from backend.excel_import import parse_resource_workbook
from backend.services import apply_excel_import


WORKBOOK_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Aug" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

WORKBOOK_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
    Target="worksheets/sheet1.xml"/>
</Relationships>"""


def inline_cell(reference: str, value: str) -> str:
    return f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def number_cell(reference: str, value: float) -> str:
    return f'<c r="{reference}"><v>{value}</v></c>'


def build_workbook() -> bytes:
    section = inline_cell("A2", "Project Alpha")
    member_cells = "".join(
        [
            inline_cell("A3", "Alice"),
            inline_cell("B3", "I07"),
            inline_cell("C3", "Platform"),
            inline_cell("D3", "Manager A"),
            inline_cell("I3", "Implementation task"),
            number_cell("J3", 0.75),
            inline_cell("O3", "Zero allocation task"),
            number_cell("P3", 0),
            inline_cell("Q3", "Hong Kong"),
            inline_cell("R3", "Resigning"),
        ]
    )
    sheet_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="2">{section}</row>
    <row r="3">{member_cells}</row>
  </sheetData>
</worksheet>"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("xl/workbook.xml", WORKBOOK_XML)
        archive.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return output.getvalue()


class ParseResourceWorkbookTests(unittest.TestCase):
    def test_maps_project_resource_columns_through_remark(self):
        preview = parse_resource_workbook(
            build_workbook(), "Project Resources Summary - Aug 26-2.xlsx"
        )

        self.assertTrue(preview["resource_month"].endswith("-08"))
        self.assertEqual(preview["stats"]["member_count"], 1)
        self.assertEqual(preview["stats"]["assignment_count"], 1)
        self.assertEqual(preview["stats"]["issue_count"], 0)

        member = preview["members"][0]
        self.assertEqual(member["role"], "I07")
        self.assertEqual(member["team"], "Platform")
        self.assertEqual(member["status"], "away")
        self.assertIn("HKPM: Manager A", member["notes"])
        self.assertIn("Area: Hong Kong", member["notes"])
        self.assertIn("Remark: Resigning", member["notes"])

        assignment = preview["assignments"][0]
        self.assertEqual(assignment["project_name"], "Project Alpha")
        self.assertEqual(assignment["stage"], "Implementation")
        self.assertEqual(assignment["project_pm_item"], "Manager A")
        self.assertEqual(assignment["task_name"], "Implementation task")
        self.assertEqual(assignment["allocation_percent"], 75)


class ApplyExcelImportTests(unittest.TestCase):
    def test_rejects_empty_assignments_before_replacing_month(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(
            """
            CREATE TABLE import_batches (id INTEGER PRIMARY KEY, resource_month TEXT);
            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY,
                source_type TEXT,
                import_batch_id INTEGER
            );
            INSERT INTO import_batches (id, resource_month) VALUES (1, '2026-08');
            INSERT INTO assignments (id, source_type, import_batch_id)
            VALUES (1, 'excel', 1);
            """
        )
        preview = {"resource_month": "2026-08", "assignments": []}

        with self.assertRaisesRegex(ValueError, "保护现有月份数据"):
            apply_excel_import(conn, preview, "replace_month")

        remaining = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
        self.assertEqual(remaining, 1)


if __name__ == "__main__":
    unittest.main()
