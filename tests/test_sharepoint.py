import io
import json
import unittest

from backend.sharepoint import preview_excel, share_token
from tests.test_excel_import import build_workbook


class Response:
    def __init__(self, content):
        self.content = content

    def read(self):
        return self.content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class SharePointPreviewTests(unittest.TestCase):
    def test_reads_excel_bytes_without_writing_a_file(self):
        share_url = "https://example.sharepoint.com/:x:/r/Documents/Plan.xlsx"

        def opener(request, timeout):
            if request.full_url.endswith("/content"):
                return Response(build_workbook())
            return Response(json.dumps({"name": "Plan.xlsx", "webUrl": share_url}).encode())

        preview = preview_excel(share_url, "token", opener)

        self.assertEqual(preview["filename"], "Plan.xlsx")
        self.assertEqual(preview["sheet_name"], "Aug")
        self.assertEqual(preview["rows"][0][0], "Project Alpha")
        self.assertTrue(share_token(share_url).startswith("u!"))


if __name__ == "__main__":
    unittest.main()
