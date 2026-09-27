import base64
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .excel_import import read_sheet


def share_token(share_url: str) -> str:
    host = urlparse(share_url).hostname or ""
    if not host.endswith(".sharepoint.com"):
        raise ValueError("请输入 SharePoint 分享链接")
    encoded = base64.b64encode(share_url.encode()).decode().rstrip("=")
    return "u!" + encoded.replace("/", "_").replace("+", "-")


def preview_excel(share_url: str, access_token: str, opener=urlopen) -> dict:
    token = share_token(share_url)
    headers = {"Authorization": f"Bearer {access_token}"}

    def get(url: str) -> bytes:
        with opener(Request(url, headers=headers), timeout=20) as response:
            return response.read()

    metadata = json.loads(get(f"https://graph.microsoft.com/v1.0/shares/{token}/driveItem"))
    filename = metadata.get("name", "sharepoint.xlsx")
    if not filename.lower().endswith(".xlsx"):
        raise ValueError("当前只支持 .xlsx 文件")
    content = get(f"https://graph.microsoft.com/v1.0/shares/{token}/driveItem/content")
    sheet_name, rows, max_row = read_sheet(content)
    column_count = max((max(row, default=0) for row in rows.values()), default=0)
    sample_rows = [
        [rows[row_number].get(column) for column in range(1, column_count + 1)]
        for row_number in sorted(rows)[:20]
    ]
    return {
        "filename": filename,
        "sheet_name": sheet_name,
        "row_count": max_row,
        "column_count": column_count,
        "rows": sample_rows,
        "web_url": metadata.get("webUrl"),
    }
