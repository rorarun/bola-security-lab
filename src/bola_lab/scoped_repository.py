"""Central SQL access with tenant, project and current membership predicates."""

from fastapi import HTTPException

from bola_lab.policy import ROLES, ProjectScope

# Fixed SQL, not interpolated caller input. All actual values are parameters.
PROJECT = """p.organization_id=%s AND p.id=%s AND EXISTS (
    SELECT 1 FROM project_memberships pm JOIN organization_memberships om
    ON om.organization_id=pm.organization_id AND om.user_id=pm.user_id
    WHERE pm.organization_id=p.organization_id AND pm.project_id=p.id AND pm.user_id=%s)"""
TASK = """t.organization_id=%s AND t.project_id=%s AND EXISTS (
    SELECT 1 FROM projects p JOIN project_memberships pm ON pm.project_id=p.id
    AND pm.organization_id=p.organization_id JOIN organization_memberships om
    ON om.organization_id=pm.organization_id AND om.user_id=pm.user_id
    WHERE p.id=t.project_id AND p.organization_id=t.organization_id AND pm.user_id=%s)"""


def resolve(conn, organization_id, project_id, actor_id, *, write=False):
    parameters = (organization_id, project_id, actor_id)
    if write:
        conn.execute(
            "SELECT p.id FROM projects p WHERE " + PROJECT + " FOR UPDATE OF p", parameters
        )
    row = conn.execute(
        """SELECT p.*, pm.role FROM projects p JOIN project_memberships pm
        ON pm.project_id=p.id AND pm.organization_id=p.organization_id
        WHERE """
        + PROJECT
        + " AND pm.user_id=%s",
        parameters + (actor_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Resource not found")
    return ProjectScope(organization_id, project_id, actor_id, row["role"]), row


def task(conn, scope, task_id):
    row = conn.execute(
        "SELECT t.* FROM tasks t WHERE " + TASK + " AND t.id=%s", scope.parameters + (task_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Resource not found")
    return row


def tasks(conn, scope):
    return conn.execute(
        "SELECT t.* FROM tasks t WHERE " + TASK + " ORDER BY t.id", scope.parameters
    ).fetchall()


def create_task(conn, scope, body):
    return conn.execute(
        """INSERT INTO tasks (organization_id,project_id,created_by,title,description,status)
        SELECT p.organization_id,p.id,%s,%s,%s,%s FROM projects p WHERE """
        + PROJECT
        + """
        AND EXISTS (SELECT 1 FROM project_memberships m WHERE m.project_id=p.id
                    AND m.user_id=%s AND m.role=ANY(%s)) RETURNING *""",
        (scope.actor_id, body.title, body.description, body.status)
        + scope.parameters
        + (scope.actor_id, sorted(ROLES["tasks.create"])),
    ).fetchone()


def update_task(conn, scope, task_id, body):
    return conn.execute(
        """UPDATE tasks t SET title=COALESCE(%s,t.title),
        description=COALESCE(%s,t.description),status=COALESCE(%s,t.status),updated_at=now()
        WHERE """
        + TASK
        + """ AND t.id=%s AND EXISTS (SELECT 1 FROM project_memberships m
        WHERE m.project_id=t.project_id AND m.user_id=%s AND m.role=ANY(%s)) RETURNING t.*""",
        (body.title, body.description, body.status)
        + scope.parameters
        + (task_id, scope.actor_id, sorted(ROLES["tasks.update"])),
    ).fetchone()


def delete_task(conn, scope, task_id):
    conn.execute(
        "DELETE FROM tasks t WHERE "
        + TASK
        + """ AND t.id=%s AND EXISTS (
        SELECT 1 FROM project_memberships m WHERE m.project_id=t.project_id
        AND m.user_id=%s AND m.role=ANY(%s))""",
        scope.parameters + (task_id, scope.actor_id, sorted(ROLES["tasks.delete"])),
    )


def require_current_action(conn, scope, action):
    roles = sorted(ROLES.get(action, frozenset()))
    if not conn.execute(
        "SELECT 1 FROM projects p WHERE "
        + PROJECT
        + """ AND EXISTS (
        SELECT 1 FROM project_memberships m WHERE m.project_id=p.id AND m.user_id=%s
        AND m.role=ANY(%s))""",
        scope.parameters + (scope.actor_id, roles),
    ).fetchone():
        raise HTTPException(403, "Insufficient project role")


def update_project(conn, scope, body):
    require_current_action(conn, scope, "project.update")
    return conn.execute(
        "UPDATE projects p SET name=COALESCE(%s,p.name),"
        "description=COALESCE(%s,p.description) WHERE " + PROJECT + " RETURNING p.*",
        (body.name, body.description) + scope.parameters,
    ).fetchone()


def delete_project(conn, scope):
    require_current_action(conn, scope, "project.delete")
    conn.execute("DELETE FROM projects p WHERE " + PROJECT, scope.parameters)


def memberships(conn, scope):
    require_current_action(conn, scope, "memberships.read")
    return conn.execute(
        "SELECT m.* FROM project_memberships m JOIN projects p ON p.id=m.project_id "
        "WHERE " + PROJECT + " ORDER BY m.user_id",
        scope.parameters,
    ).fetchall()


def membership(conn, scope, user_id):
    require_current_action(conn, scope, "memberships.read")
    row = conn.execute(
        "SELECT m.* FROM project_memberships m JOIN projects p ON p.id=m.project_id "
        "WHERE " + PROJECT + " AND m.user_id=%s",
        scope.parameters + (user_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Resource not found")
    return row


def add_member(conn, scope, body):
    require_current_action(conn, scope, "memberships.add")
    row = conn.execute(
        """INSERT INTO project_memberships (organization_id,project_id,user_id,role)
        SELECT p.organization_id,p.id,%s,%s FROM projects p WHERE """
        + PROJECT
        + """ AND EXISTS (
        SELECT 1 FROM organization_memberships om WHERE om.organization_id=p.organization_id
        AND om.user_id=%s) ON CONFLICT DO NOTHING RETURNING *""",
        (body.user_id, body.role) + scope.parameters + (body.user_id,),
    ).fetchone()
    if row is None:
        if not conn.execute(
            "SELECT 1 FROM organization_memberships WHERE organization_id=%s AND user_id=%s",
            (scope.organization_id, body.user_id),
        ).fetchone():
            raise HTTPException(404, "Resource not found")
        raise HTTPException(409, "Project membership already exists")
    return row


def change_member(conn, scope, user_id, role=None):
    require_current_action(
        conn, scope, "memberships.delete" if role is None else "memberships.update"
    )
    row = membership(conn, scope, user_id)
    if row["role"] == "owner":
        raise HTTPException(409, "Owner cannot be removed, demoted or transferred")
    if role is None:
        conn.execute(
            "DELETE FROM project_memberships m USING projects p WHERE m.project_id=p.id AND "
            + PROJECT
            + " AND m.user_id=%s",
            scope.parameters + (user_id,),
        )
        return None
    return conn.execute(
        "UPDATE project_memberships m SET role=%s FROM projects p WHERE m.project_id=p.id AND "
        + PROJECT
        + " AND m.user_id=%s RETURNING m.*",
        (role,) + scope.parameters + (user_id,),
    ).fetchone()
