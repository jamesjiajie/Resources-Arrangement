import hashlib
import io
import re
import zipfile
from datetime import date
from typing import Any
from xml.etree import ElementTree


STAGE_COLUMNS = [
    ("Requirement", 4, 5),
    ("Design", 6, 7),
    ("Implementation", 8, 9),
    ("Testing", 10, 11),
    ("Deployment", 12, 13),
    ("Maintenance", 14, 15),
]

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_number(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        number = float(text.replace("%", ""))
        return number / 100 if "%" in text else number
    except ValueError:
        return None


def column_index(cell_ref: str) -> int:
    letters = re.match(r"([A-Z]+)", cell_ref).group(1)
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index


def read_shared_strings(archive: zipfile.ZipFile):
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    values = []
    for item in root.findall("main:si", NS):
        texts = [node.text or "" for node in item.findall(".//main:t", NS)]
        values.append("".join(texts))
    return values


def first_sheet_path(archive: zipfile.ZipFile):
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    first_sheet = workbook.find("main:sheets/main:sheet", NS)
    sheet_name = first_sheet.attrib["name"]
    rel_id = first_sheet.attrib[f"{{{NS['rel']}}}id"]
    targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("pkgrel:Relationship", NS)}
    target = targets[rel_id]
    if target.startswith("/"):
        path = target.lstrip("/")
    else:
        path = "xl/" + target
    return sheet_name, path.replace("xl/xl/", "xl/")


def cell_value(cell, shared_strings):
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", NS))
    value_node = cell.find("main:v", NS)
    if value_node is None:
        return None
    raw_value = value_node.text or ""
    if cell_type == "s":
        return shared_strings[int(raw_value)]
    if cell_type == "b":
        return raw_value == "1"
    try:
        number = float(raw_value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return raw_value


def read_sheet(content: bytes):
    archive = zipfile.ZipFile(io.BytesIO(content))
    shared_strings = read_shared_strings(archive)
    sheet_name, sheet_path = first_sheet_path(archive)
    root = ElementTree.fromstring(archive.read(sheet_path))
    rows = {}
    max_row = 0
    for row in root.findall(".//main:sheetData/main:row", NS):
        row_number = int(row.attrib["r"])
        max_row = max(max_row, row_number)
        row_values = {}
        for cell in row.findall("main:c", NS):
            row_values[column_index(cell.attrib["r"])] = cell_value(cell, shared_strings)
        rows[row_number] = row_values
    return sheet_name, rows, max_row


def infer_resource_month(filename: str, sheet_name: str) -> str:
    text = f"{filename} {sheet_name}"
    year_match = re.search(r"\b(20\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else date.today().year
    month_names = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }
    lowered = text.casefold()
    month = None
    for name, number in month_names.items():
        if re.search(rf"\b{name}\b", lowered):
            month = number
            break
    if month is None:
        numeric = re.search(r"\b(0?[1-9]|1[0-2])\b", text)
        month = int(numeric.group(1)) if numeric else date.today().month
    return f"{year:04d}-{month:02d}"


def month_dates(resource_month: str):
    year, month = [int(part) for part in resource_month.split("-")]
    start = date(year, month, 1)
    next_month = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    end = date.fromordinal(next_month.toordinal() - 1)
    return start.isoformat(), end.isoformat()


def row_values(rows, row_number: int):
    row = rows.get(row_number, {})
    return [row.get(column) for column in range(1, 18)]


def parse_resource_workbook(content: bytes, filename: str) -> dict:
    sheet_name, rows, max_row = read_sheet(content)
    resource_month = infer_resource_month(filename, sheet_name)
    start_date, end_date = month_dates(resource_month)
    digest = hashlib.sha256(content).hexdigest()[:16]

    sections = []
    members = {}
    projects = {}
    assignments = []
    issues = []
    current_section = ""

    for row_number in range(2, max_row + 1):
        values = row_values(rows, row_number)
        first = clean_text(values[0])
        if not first:
            continue
        if all(value is None or clean_text(value) == "" for value in values[1:]):
            current_section = first
            sections.append({"row": row_number, "name": current_section})
            projects[normalize_key(current_section)] = {
                "name": current_section,
                "code": "",
                "owner": "",
                "status": "active",
                "priority": "medium",
                "start_date": start_date,
                "end_date": end_date,
                "notes": f"Imported from {filename} / {sheet_name}.",
                "source_row": row_number,
            }
            continue

        level = clean_text(values[1])
        hkpm = clean_text(values[2])
        area = clean_text(values[15])
        remark = clean_text(values[16])
        member_key = normalize_key(first)
        member_notes = []
        if level:
            member_notes.append(f"Level: {level}")
        if hkpm:
            member_notes.append(f"HKPM: {hkpm}")
        if area:
            member_notes.append(f"Area: {area}")
        if remark:
            member_notes.append(f"Remark: {remark}")
        members[member_key] = {
            "name": first,
            "role": level,
            "team": area,
            "capacity_hours_week": 40,
            "status": "away" if "resign" in remark.casefold() else "available",
            "notes": "; ".join(member_notes),
            "source_row": row_number,
        }

        if current_section:
            project = projects.setdefault(
                normalize_key(current_section),
                {
                    "name": current_section,
                    "code": "",
                    "owner": hkpm,
                    "status": "active",
                    "priority": "medium",
                    "start_date": start_date,
                    "end_date": end_date,
                    "notes": f"Imported from {filename} / {sheet_name}.",
                    "source_row": row_number,
                },
            )
            if hkpm and not project["owner"]:
                project["owner"] = hkpm

        for stage, task_column, fte_column in STAGE_COLUMNS:
            task = clean_text(values[task_column - 1])
            fte = parse_number(values[fte_column - 1])
            if not task and fte is None:
                continue
            if fte is None:
                issues.append(
                    {
                        "level": "warning",
                        "row": row_number,
                        "message": f"{first} 的 {stage} 有任务但没有 FTE，已在预览中保留但默认不写入安排。",
                    }
                )
                continue
            if not task:
                task = f"{current_section} - {stage}"
            notes = [f"Stage: {stage}", f"Source: {sheet_name}!{row_number}"]
            if hkpm:
                notes.append(f"HKPM: {hkpm}")
            if area:
                notes.append(f"Area: {area}")
            if remark:
                notes.append(f"Remark: {remark}")
            assignments.append(
                {
                    "source_key": f"{resource_month}|{sheet_name}|{row_number}|{stage}",
                    "row": row_number,
                    "member_name": first,
                    "project_name": current_section or "未分组",
                    "task_name": task,
                    "stage": stage,
                    "fte": fte,
                    "allocation_percent": round(fte * 100, 2),
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": "active",
                    "priority": "medium",
                    "notes": "; ".join(notes),
                }
            )

    if not assignments:
        issues.append({"level": "error", "row": None, "message": "没有识别到可导入的 FTE 安排。"})

    return {
        "filename": filename,
        "file_hash": digest,
        "sheet_name": sheet_name,
        "resource_month": resource_month,
        "start_date": start_date,
        "end_date": end_date,
        "sections": sections,
        "members": list(members.values()),
        "projects": list(projects.values()),
        "assignments": assignments,
        "issues": issues,
        "stats": {
            "section_count": len(sections),
            "member_count": len(members),
            "project_count": len(projects),
            "assignment_count": len(assignments),
            "issue_count": len(issues),
        },
    }
