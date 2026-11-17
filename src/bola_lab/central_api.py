"""Thin HTTP adapters. All authorization decisions belong to the central service/policy."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, Response

from bola_lab.central_service import execute
from bola_lab.identity import authenticated_user
from bola_lab.resources import (
    MembershipCreate,
    MembershipPatch,
    MembershipResponse,
    OrganizationCreate,
    OrganizationResponse,
    ProjectCreate,
    ProjectPatch,
    ProjectResponse,
    TaskCreate,
    TaskPatch,
    TaskResponse,
)

router = APIRouter(prefix="/organizations", tags=["Task management"])
Actor = Annotated[dict, Depends(authenticated_user)]
Identifier = Annotated[int, Path(gt=0, le=9223372036854775807)]


@router.post("", response_model=OrganizationResponse, status_code=201)
def create_organization(body: OrganizationCreate, request: Request, user: Actor):
    return execute(request.app.state.settings, user["id"], "organizations.create", body=body)


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(request: Request, user: Actor):
    return execute(request.app.state.settings, user["id"], "organizations.list")


@router.get("/{org_id}", response_model=OrganizationResponse)
def read_organization(org_id: Identifier, request: Request, user: Actor):
    return execute(request.app.state.settings, user["id"], "organizations.read", org_id=org_id)


@router.post("/{org_id}/projects", response_model=ProjectResponse, status_code=201)
def create_project(org_id: Identifier, body: ProjectCreate, request: Request, user: Actor):
    return execute(
        request.app.state.settings, user["id"], "projects.create", org_id=org_id, body=body
    )


@router.get("/{org_id}/projects", response_model=list[ProjectResponse])
def list_projects(org_id: Identifier, request: Request, user: Actor):
    return execute(request.app.state.settings, user["id"], "projects.list", org_id=org_id)


@router.get("/{org_id}/projects/{project_id}", response_model=ProjectResponse)
def read_project(org_id: Identifier, project_id: Identifier, request: Request, user: Actor):
    return execute(
        request.app.state.settings,
        user["id"],
        "projects.read",
        org_id=org_id,
        project_id=project_id,
    )


@router.patch("/{org_id}/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    org_id: Identifier, project_id: Identifier, body: ProjectPatch, request: Request, user: Actor
):
    return execute(
        request.app.state.settings,
        user["id"],
        "projects.update",
        org_id=org_id,
        project_id=project_id,
        body=body,
    )


@router.delete("/{org_id}/projects/{project_id}", status_code=204)
def delete_project(org_id: Identifier, project_id: Identifier, request: Request, user: Actor):
    execute(
        request.app.state.settings,
        user["id"],
        "projects.delete",
        org_id=org_id,
        project_id=project_id,
    )
    return Response(status_code=204)


@router.get("/{org_id}/projects/{project_id}/memberships", response_model=list[MembershipResponse])
def list_memberships(org_id: Identifier, project_id: Identifier, request: Request, user: Actor):
    return execute(
        request.app.state.settings,
        user["id"],
        "memberships.read",
        org_id=org_id,
        project_id=project_id,
    )


@router.post(
    "/{org_id}/projects/{project_id}/memberships",
    response_model=MembershipResponse,
    status_code=201,
)
def add_membership(
    org_id: Identifier,
    project_id: Identifier,
    body: MembershipCreate,
    request: Request,
    user: Actor,
):
    return execute(
        request.app.state.settings,
        user["id"],
        "memberships.add",
        org_id=org_id,
        project_id=project_id,
        body=body,
    )


@router.patch(
    "/{org_id}/projects/{project_id}/memberships/{user_id}", response_model=MembershipResponse
)
def update_membership(
    org_id: Identifier,
    project_id: Identifier,
    user_id: Identifier,
    body: MembershipPatch,
    request: Request,
    user: Actor,
):
    return execute(
        request.app.state.settings,
        user["id"],
        "memberships.update",
        org_id=org_id,
        project_id=project_id,
        body=body,
        item_id=user_id,
    )


@router.delete("/{org_id}/projects/{project_id}/memberships/{user_id}", status_code=204)
def revoke_membership(
    org_id: Identifier, project_id: Identifier, user_id: Identifier, request: Request, user: Actor
):
    execute(
        request.app.state.settings,
        user["id"],
        "memberships.delete",
        org_id=org_id,
        project_id=project_id,
        item_id=user_id,
    )
    return Response(status_code=204)


@router.post("/{org_id}/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    org_id: Identifier, project_id: Identifier, body: TaskCreate, request: Request, user: Actor
):
    return execute(
        request.app.state.settings,
        user["id"],
        "tasks.create",
        org_id=org_id,
        project_id=project_id,
        body=body,
    )


@router.get("/{org_id}/projects/{project_id}/tasks", response_model=list[TaskResponse])
def list_tasks(org_id: Identifier, project_id: Identifier, request: Request, user: Actor):
    return execute(
        request.app.state.settings, user["id"], "tasks.list", org_id=org_id, project_id=project_id
    )


@router.get("/{org_id}/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def read_task(
    org_id: Identifier, project_id: Identifier, task_id: Identifier, request: Request, user: Actor
):
    return execute(
        request.app.state.settings,
        user["id"],
        "tasks.read",
        org_id=org_id,
        project_id=project_id,
        item_id=task_id,
    )


@router.patch("/{org_id}/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    org_id: Identifier,
    project_id: Identifier,
    task_id: Identifier,
    body: TaskPatch,
    request: Request,
    user: Actor,
):
    return execute(
        request.app.state.settings,
        user["id"],
        "tasks.update",
        org_id=org_id,
        project_id=project_id,
        body=body,
        item_id=task_id,
    )


@router.delete("/{org_id}/projects/{project_id}/tasks/{task_id}", status_code=204)
def delete_task(
    org_id: Identifier, project_id: Identifier, task_id: Identifier, request: Request, user: Actor
):
    execute(
        request.app.state.settings,
        user["id"],
        "tasks.delete",
        org_id=org_id,
        project_id=project_id,
        item_id=task_id,
    )
    return Response(status_code=204)
