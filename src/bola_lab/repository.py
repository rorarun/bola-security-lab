"""Reusable data/business operations; no permission decisions.

The M2 endpoint implementation must check the returned context explicitly. In particular,
project_context returns projects even for outsiders; it is NOT an authorized-object loader.
Centralized tenant-scoped authorization is deliberately deferred to M4.
"""


def organization_member(conn, organization_id, user_id):
    return (
        conn.execute(
            "SELECT 1 FROM organization_memberships WHERE organization_id=%s AND user_id=%s",
            (organization_id, user_id),
        ).fetchone()
        is not None
    )


def create_organization(conn, name, user_id):
    organization = conn.execute(
        "INSERT INTO organizations (name,created_by) VALUES (%s,%s) RETURNING *",
        (name, user_id),
    ).fetchone()
    conn.execute(
        "INSERT INTO organization_memberships VALUES (%s,%s)", (organization["id"], user_id)
    )
    return organization


def lock_project(conn, project_id):
    # Separate statement: membership is read on a fresh snapshot after any lock wait.
    conn.execute("SELECT id FROM projects WHERE id=%s FOR UPDATE", (project_id,)).fetchone()


def project_context(conn, organization_id, project_id, user_id):
    return conn.execute(
        """SELECT p.*, pm.role,
           EXISTS(SELECT 1 FROM organization_memberships om
                  WHERE om.organization_id=%s AND om.user_id=%s) AS organization_member
           FROM projects p LEFT JOIN project_memberships pm ON pm.project_id=p.id AND pm.user_id=%s
           WHERE p.id=%s""",
        (organization_id, user_id, user_id, project_id),
    ).fetchone()


def create_project(conn, organization_id, user_id, name, description):
    project = conn.execute(
        """INSERT INTO projects (organization_id,created_by,name,description)
           VALUES (%s,%s,%s,%s) RETURNING *""",
        (organization_id, user_id, name, description),
    ).fetchone()
    conn.execute(
        "INSERT INTO project_memberships VALUES (%s,%s,%s,'owner')",
        (organization_id, project["id"], user_id),
    )
    return project


def update_project(conn, project_id, name, description):
    return conn.execute(
        """UPDATE projects SET name=COALESCE(%s,name), description=COALESCE(%s,description)
           WHERE id=%s RETURNING *""",
        (name, description, project_id),
    ).fetchone()


def task(conn, task_id):
    return conn.execute("SELECT * FROM tasks WHERE id=%s", (task_id,)).fetchone()


def create_task(conn, organization_id, project_id, user_id, title, description, status):
    return conn.execute(
        """INSERT INTO tasks (organization_id,project_id,created_by,title,description,status)
           VALUES (%s,%s,%s,%s,%s,%s) RETURNING *""",
        (organization_id, project_id, user_id, title, description, status),
    ).fetchone()


def update_task(conn, task_id, title, description, status):
    return conn.execute(
        """UPDATE tasks SET title=COALESCE(%s,title), description=COALESCE(%s,description),
           status=COALESCE(%s,status), updated_at=now() WHERE id=%s RETURNING *""",
        (title, description, status, task_id),
    ).fetchone()
