"""Central enforcement and transaction service, independent from endpoint-specific checks."""

from fastapi import HTTPException

from bola_lab import repository as business
from bola_lab import scoped_repository as data
from bola_lab.db import connect
from bola_lab.policy import authorize


def execute(settings, actor, operation, *, org_id=None, project_id=None, item_id=None, body=None):
    with connect(settings) as conn:
        if operation == "organizations.create":
            return business.create_organization(conn, body.name, actor)
        if operation == "organizations.list":
            return conn.execute(
                """SELECT o.* FROM organizations o JOIN organization_memberships m
                ON m.organization_id=o.id WHERE m.user_id=%s ORDER BY o.id""",
                (actor,),
            ).fetchall()
        if operation in {"organizations.read", "projects.create", "projects.list"}:
            org = conn.execute(
                """SELECT o.* FROM organizations o JOIN organization_memberships m
                ON m.organization_id=o.id WHERE o.id=%s AND m.user_id=%s""",
                (org_id, actor),
            ).fetchone()
            if org is None:
                raise HTTPException(404, "Resource not found")
            if operation == "organizations.read":
                return org
            if operation == "projects.create":
                return business.create_project(conn, org_id, actor, body.name, body.description)
            return conn.execute(
                """SELECT p.* FROM projects p JOIN project_memberships m
                ON m.project_id=p.id AND m.organization_id=p.organization_id
                WHERE p.organization_id=%s AND m.user_id=%s ORDER BY p.id""",
                (org_id, actor),
            ).fetchall()
        action = {
            "projects.read": "project.read",
            "projects.update": "project.update",
            "projects.delete": "project.delete",
            "tasks.list": "tasks.read",
        }.get(operation, operation)
        write = operation.rsplit(".", 1)[-1] not in {"read", "list"}
        scope, project = data.resolve(conn, org_id, project_id, actor, write=write)
        target = None
        if operation in {"tasks.read", "tasks.update", "tasks.delete"}:
            target = data.task(conn, scope, item_id)
        authorize(scope, action)
        if operation == "projects.read":
            return project
        if operation == "projects.update":
            return data.update_project(conn, scope, body)
        if operation == "projects.delete":
            return data.delete_project(conn, scope)
        if operation == "tasks.list":
            return data.tasks(conn, scope)
        if operation == "tasks.read":
            return target
        if operation == "tasks.create":
            return data.create_task(conn, scope, body)
        if operation == "tasks.update":
            return data.update_task(conn, scope, item_id, body)
        if operation == "tasks.delete":
            return data.delete_task(conn, scope, item_id)
        if operation == "memberships.read":
            return data.memberships(conn, scope)
        if operation == "memberships.add":
            return data.add_member(conn, scope, body)
        if operation == "memberships.update":
            return data.change_member(conn, scope, item_id, body.role)
        if operation == "memberships.delete":
            return data.change_member(conn, scope, item_id)
        raise HTTPException(403, "Insufficient project role")
