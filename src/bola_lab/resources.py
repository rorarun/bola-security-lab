"""Resource contracts. Identity/tenant/ownership are never writable body fields."""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Description = Annotated[str, Field(max_length=4000)]
NonOwnerRole = Literal["editor", "viewer"]
TaskStatus = Literal["todo", "in_progress", "done"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class OrganizationCreate(Input):
    name: Name


class OrganizationResponse(BaseModel):
    id: int
    name: str
    created_by: int
    created_at: datetime


class ProjectCreate(Input):
    name: Name
    description: Description = ""


class ProjectResponse(OrganizationResponse):
    organization_id: int
    description: str


class NonEmptyPatch(Input):
    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        if not self.model_fields_set or any(
            getattr(self, key) is None for key in self.model_fields_set
        ):
            raise ValueError("Provide at least one field; explicit null values are not supported")
        return self


class ProjectPatch(NonEmptyPatch):
    name: Name | None = None
    description: Description | None = None


class MembershipCreate(Input):
    user_id: int = Field(gt=0, le=9223372036854775807)
    role: NonOwnerRole


class MembershipPatch(Input):
    role: NonOwnerRole


class MembershipResponse(BaseModel):
    organization_id: int
    project_id: int
    user_id: int
    role: Literal["owner", "editor", "viewer"]


class TaskCreate(Input):
    title: Title
    description: Description = ""
    status: TaskStatus = "todo"


class TaskPatch(NonEmptyPatch):
    title: Title | None = None
    description: Description | None = None
    status: TaskStatus | None = None


class TaskResponse(BaseModel):
    id: int
    organization_id: int
    project_id: int
    title: str
    description: str
    status: TaskStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
