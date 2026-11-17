"""Five labelled omissions, gated to the harness-owned synthetic laboratory."""

import os
import socket
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from bola_lab import repository
from bola_lab.config import Settings
from bola_lab.db import connect
from bola_lab.endpoint_api import Identifier
from bola_lab.endpoint_api import router as endpoint_router
from bola_lab.evaluation.runner import evaluation_settings
from bola_lab.identity import authenticated_user
from bola_lab.main import create_authenticated_app
from bola_lab.resources import TaskCreate, TaskPatch, TaskResponse

Actor = Annotated[dict, Depends(authenticated_user)]
router = APIRouter()
PATH = "/organizations/{org_id}/projects/{project_id}/tasks"


def create_lab_app():
    if os.environ.get("BOLA_LOCAL_DEFECT_LAB") != "explicit-synthetic-lab-only":
        raise ValueError("Explicit laboratory opt-in required")
    if (
        os.environ.get("BOLA_ENVIRONMENT") != "lab"
        or os.environ.get("BOLA_BIND_HOST") != "127.0.0.1"
    ):
        raise ValueError("Local lab environment and loopback bind required")
    evaluation_settings(os.environ["BOLA_DATABASE_URL"])
    # Check the actual inherited listener, not just an environment assertion.
    with socket.fromfd(
        int(os.environ["BOLA_LAB_LISTENER_FD"]), socket.AF_INET, socket.SOCK_STREAM
    ) as listener:
        if listener.getsockname()[0] != "127.0.0.1":
            raise ValueError("Baseline listener is not loopback")
    settings = Settings(
        database_url=os.environ["BOLA_DATABASE_URL"],
        environment="lab",
        lab_opt_in=True,
        authorization_mode="endpoint",
    )
    app = create_authenticated_app(settings)
    selected = {
        (PATH, "GET"),
        (PATH, "POST"),
        (PATH + "/{task_id}", "GET"),
        (PATH + "/{task_id}", "PATCH"),
        (PATH + "/{task_id}", "DELETE"),
    }
    combined = APIRouter()
    combined.routes.extend(
        r
        for r in endpoint_router.routes
        if not any(
            (getattr(r, "path", None), method) in selected
            for method in getattr(r, "methods", set())
        )
    )
    combined.routes.extend(router.routes)
    app.include_router(combined)
    app.state.authorization_implementation = "labelled-local-baseline"
    return app


@router.get(PATH + "/{task_id}", response_model=TaskResponse)
def detail(
    org_id: Identifier, project_id: Identifier, task_id: Identifier, request: Request, user: Actor
):
    with connect(request.app.state.settings) as conn:
        row = repository.task(conn, task_id)  # B01: intentionally no caller/parent scope.
        if row is None:
            raise HTTPException(404, "Resource not found")
    return row


@router.get(PATH, response_model=list[TaskResponse])
def listing(org_id: Identifier, project_id: Identifier, request: Request, user: Actor):
    with connect(request.app.state.settings) as conn:
        if not conn.execute(
            "SELECT 1 FROM projects WHERE id=%s AND organization_id=%s", (project_id, org_id)
        ).fetchone():
            raise HTTPException(404, "Resource not found")
        return conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()  # B02


@router.patch(PATH + "/{task_id}", response_model=TaskResponse)
def update(
    org_id: Identifier,
    project_id: Identifier,
    task_id: Identifier,
    body: TaskPatch,
    request: Request,
    user: Actor,
):
    with connect(request.app.state.settings) as conn:
        if repository.task(conn, task_id) is None:
            raise HTTPException(404, "Resource not found")
        return repository.update_task(
            conn, task_id, body.title, body.description, body.status
        )  # B03


@router.delete(PATH + "/{task_id}", status_code=204)
def delete(
    org_id: Identifier, project_id: Identifier, task_id: Identifier, request: Request, user: Actor
):
    with connect(request.app.state.settings) as conn:
        if repository.task(conn, task_id) is None:
            raise HTTPException(404, "Resource not found")
        conn.execute("DELETE FROM tasks WHERE id=%s", (task_id,))  # B04, parameterization retained.
    return Response(status_code=204)


@router.post(PATH, response_model=TaskResponse, status_code=201)
def create(
    org_id: Identifier, project_id: Identifier, body: TaskCreate, request: Request, user: Actor
):
    with connect(request.app.state.settings) as conn:
        if not conn.execute(
            "SELECT 1 FROM projects WHERE id=%s AND organization_id=%s", (project_id, org_id)
        ).fetchone():
            raise HTTPException(404, "Resource not found")
        return repository.create_task(
            conn, org_id, project_id, user["id"], body.title, body.description, body.status
        )  # B05
