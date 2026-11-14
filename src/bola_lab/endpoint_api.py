"""M2 endpoint-specific authorization.

Each operation explicitly checks its own object scope and role. Repository helpers return raw data,
not authorized objects. Keep these checks separate from the future centralized implementation.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response

from bola_lab import repository as db
from bola_lab.db import connect
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
    with connect(request.app.state.settings) as conn:
        result = db.create_organization(conn, body.name, user["id"])
    return result


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(request: Request, user: Actor):
    with connect(request.app.state.settings) as conn:
        result = conn.execute(
            """SELECT o.* FROM organizations o JOIN organization_memberships m
               ON m.organization_id=o.id WHERE m.user_id=%s ORDER BY o.id""",
            (user["id"],),
        ).fetchall()
    return result


@router.get("/{org_id}", response_model=OrganizationResponse)
def read_organization(org_id: Identifier, request: Request, user: Actor):
    with connect(request.app.state.settings) as conn:
        if not db.organization_member(conn, org_id, user["id"]):
            raise HTTPException(404, "Resource not found")
        result = conn.execute("SELECT * FROM organizations WHERE id=%s", (org_id,)).fetchone()
    return result


@router.post("/{org_id}/projects", response_model=ProjectResponse, status_code=201)
def create_project(org_id: Identifier, body: ProjectCreate, request: Request, user: Actor):
    with connect(request.app.state.settings) as conn:
        if not db.organization_member(conn, org_id, user["id"]):
            raise HTTPException(404, "Resource not found")
        result = db.create_project(conn, org_id, user["id"], body.name, body.description)
    return result


@router.get("/{org_id}/projects", response_model=list[ProjectResponse])
def list_projects(org_id: Identifier, request: Request, user: Actor):
    with connect(request.app.state.settings) as conn:
        if not db.organization_member(conn, org_id, user["id"]):
            raise HTTPException(404, "Resource not found")
        result = conn.execute(
            """SELECT p.* FROM projects p JOIN project_memberships m ON m.project_id=p.id
               WHERE p.organization_id=%s AND m.user_id=%s ORDER BY p.id""",
            (org_id, user["id"]),
        ).fetchall()
    return result


@router.get("/{org_id}/projects/{project_id}", response_model=ProjectResponse)
def read_project(org_id: Identifier, project_id: Identifier, request: Request, user: Actor):
    with connect(request.app.state.settings) as conn:
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
    return project


@router.patch("/{org_id}/projects/{project_id}", response_model=ProjectResponse)
def update_project(
    org_id: Identifier, project_id: Identifier, body: ProjectPatch, request: Request, user: Actor
):
    with connect(request.app.state.settings) as conn:
        db.lock_project(conn, project_id)
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        if project["role"] != "owner":
            raise HTTPException(403, "Insufficient project role")
        result = db.update_project(conn, project_id, body.name, body.description)
    return result


@router.delete("/{org_id}/projects/{project_id}", status_code=204)
def delete_project(org_id: Identifier, project_id: Identifier, request: Request, user: Actor):
    with connect(request.app.state.settings) as conn:
        db.lock_project(conn, project_id)
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        if project["role"] != "owner":
            raise HTTPException(403, "Insufficient project role")
        conn.execute("DELETE FROM projects WHERE id=%s", (project_id,))
    return Response(status_code=204)


@router.get("/{org_id}/projects/{project_id}/memberships", response_model=list[MembershipResponse])
def list_memberships(org_id: Identifier, project_id: Identifier, request: Request, user: Actor):
    with connect(request.app.state.settings) as conn:
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        if project["role"] != "owner":
            raise HTTPException(403, "Insufficient project role")
        result = conn.execute(
            "SELECT * FROM project_memberships WHERE project_id=%s ORDER BY user_id", (project_id,)
        ).fetchall()
    return result


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
    with connect(request.app.state.settings) as conn:
        db.lock_project(conn, project_id)
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        if project["role"] != "owner":
            raise HTTPException(403, "Insufficient project role")
        if not db.organization_member(conn, org_id, body.user_id):
            raise HTTPException(404, "Resource not found")
        result = conn.execute(
            """INSERT INTO project_memberships VALUES (%s,%s,%s,%s)
               ON CONFLICT DO NOTHING RETURNING *""",
            (org_id, project_id, body.user_id, body.role),
        ).fetchone()
        if result is None:
            raise HTTPException(409, "Project membership already exists")
    return result


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
    with connect(request.app.state.settings) as conn:
        db.lock_project(conn, project_id)
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        if project["role"] != "owner":
            raise HTTPException(403, "Insufficient project role")
        membership = conn.execute(
            "SELECT * FROM project_memberships WHERE project_id=%s AND user_id=%s",
            (project_id, user_id),
        ).fetchone()
        if membership is None:
            raise HTTPException(404, "Resource not found")
        if membership["role"] == "owner":
            raise HTTPException(409, "Owner cannot be removed, demoted or transferred")
        result = conn.execute(
            "UPDATE project_memberships SET role=%s WHERE project_id=%s AND user_id=%s RETURNING *",
            (body.role, project_id, user_id),
        ).fetchone()
    return result


@router.delete("/{org_id}/projects/{project_id}/memberships/{user_id}", status_code=204)
def revoke_membership(
    org_id: Identifier, project_id: Identifier, user_id: Identifier, request: Request, user: Actor
):
    with connect(request.app.state.settings) as conn:
        db.lock_project(conn, project_id)
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        if project["role"] != "owner":
            raise HTTPException(403, "Insufficient project role")
        membership = conn.execute(
            "SELECT * FROM project_memberships WHERE project_id=%s AND user_id=%s",
            (project_id, user_id),
        ).fetchone()
        if membership is None:
            raise HTTPException(404, "Resource not found")
        if membership["role"] == "owner":
            raise HTTPException(409, "Owner cannot be removed, demoted or transferred")
        conn.execute(
            "DELETE FROM project_memberships WHERE project_id=%s AND user_id=%s",
            (project_id, user_id),
        )
    return Response(status_code=204)


@router.post("/{org_id}/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    org_id: Identifier, project_id: Identifier, body: TaskCreate, request: Request, user: Actor
):
    with connect(request.app.state.settings) as conn:
        db.lock_project(conn, project_id)
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        if project["role"] not in {"owner", "editor"}:
            raise HTTPException(403, "Insufficient project role")
        result = db.create_task(
            conn, org_id, project_id, user["id"], body.title, body.description, body.status
        )
    return result


@router.get("/{org_id}/projects/{project_id}/tasks", response_model=list[TaskResponse])
def list_tasks(org_id: Identifier, project_id: Identifier, request: Request, user: Actor):
    with connect(request.app.state.settings) as conn:
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        result = conn.execute(
            "SELECT * FROM tasks WHERE organization_id=%s AND project_id=%s ORDER BY id",
            (org_id, project_id),
        ).fetchall()
    return result


@router.get("/{org_id}/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def read_task(
    org_id: Identifier, project_id: Identifier, task_id: Identifier, request: Request, user: Actor
):
    with connect(request.app.state.settings) as conn:
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        result = db.task(conn, task_id)
        if (
            result is None
            or result["organization_id"] != org_id
            or result["project_id"] != project_id
        ):
            raise HTTPException(404, "Resource not found")
    return result


@router.patch("/{org_id}/projects/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    org_id: Identifier,
    project_id: Identifier,
    task_id: Identifier,
    body: TaskPatch,
    request: Request,
    user: Actor,
):
    with connect(request.app.state.settings) as conn:
        db.lock_project(conn, project_id)
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        task = db.task(conn, task_id)
        if task is None or task["organization_id"] != org_id or task["project_id"] != project_id:
            raise HTTPException(404, "Resource not found")
        if project["role"] not in {"owner", "editor"}:
            raise HTTPException(403, "Insufficient project role")
        result = db.update_task(conn, task_id, body.title, body.description, body.status)
    return result


@router.delete("/{org_id}/projects/{project_id}/tasks/{task_id}", status_code=204)
def delete_task(
    org_id: Identifier, project_id: Identifier, task_id: Identifier, request: Request, user: Actor
):
    with connect(request.app.state.settings) as conn:
        db.lock_project(conn, project_id)
        project = db.project_context(conn, org_id, project_id, user["id"])
        if (
            project is None
            or project["organization_id"] != org_id
            or not project["organization_member"]
            or project["role"] is None
        ):
            raise HTTPException(404, "Resource not found")
        task = db.task(conn, task_id)
        if task is None or task["organization_id"] != org_id or task["project_id"] != project_id:
            raise HTTPException(404, "Resource not found")
        if project["role"] != "owner":
            raise HTTPException(403, "Insufficient project role")
        conn.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    return Response(status_code=204)
