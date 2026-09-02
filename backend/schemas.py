from typing import Optional

from pydantic import BaseModel, Field


class MemberIn(BaseModel):
    name: str = Field(min_length=1)
    role: str = ""
    team: str = ""
    capacity_hours_week: float = Field(default=40, gt=0, le=120)
    status: str = "available"
    notes: str = ""


class ProjectIn(BaseModel):
    name: str = Field(min_length=1)
    code: str = ""
    owner: str = ""
    status: str = "active"
    priority: str = "medium"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: str = ""


class AssignmentIn(BaseModel):
    member_id: int
    project_id: int
    project_pm_item: str = ""
    task_name: str = Field(min_length=1)
    allocation_percent: float = Field(default=50, ge=0, le=200)
    start_date: str = Field(min_length=1)
    end_date: Optional[str] = None
    status: str = "active"
    priority: str = "medium"
    notes: str = ""


class LongTermTaskIn(BaseModel):
    title: str = Field(min_length=1)
    owner: str = ""
    category: str = ""
    status: str = "active"
    priority: str = "medium"
    progress: int = Field(default=0, ge=0, le=100)
    start_date: Optional[str] = None
    target_date: Optional[str] = None
    notes: str = ""
