"""Deterministic, synthetic lab identities; never runs automatically on server startup."""

from psycopg import sql

from bola_lab.auth import hash_password
from bola_lab.config import Settings
from bola_lab.db import connect

SEED_PASSWORD = "Synthetic-Lab-Only-2026!"
SEED_TIME = "2026-11-14T12:00:00Z"
USERS = (
    (1, "owner@alpha.example"),
    (2, "editor@alpha.example"),
    (3, "viewer@alpha.example"),
    (4, "outsider@alpha.example"),
    (5, "owner@beta.example"),
    (6, "removed@alpha.example"),
    (7, "second-owner@alpha.example"),
)


def seed(settings: Settings, *, reset: bool = False) -> None:
    if settings.environment != "lab" or not settings.lab_opt_in:
        raise ValueError("Synthetic seed requires environment=lab and explicit lab_opt_in")
    with connect(settings) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(3123001)")
        if reset:
            conn.execute(
                "TRUNCATE users, organizations, organization_memberships, projects, "
                "project_memberships, tasks, auth_sessions RESTART IDENTITY CASCADE"
            )
        if conn.execute("SELECT EXISTS (SELECT 1 FROM users) AS populated").fetchone()["populated"]:
            raise ValueError("Database is not empty; --reset explicitly destroys existing lab data")
        # Hashes intentionally use fresh salts. IDs/content/times, not cryptographic randomness,
        # define fixture equivalence across future experimental configurations.
        for user_id, email in USERS:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, created_at) VALUES (%s,%s,%s,%s)",
                (user_id, email, hash_password(SEED_PASSWORD), SEED_TIME),
            )
        for org_id, name, creator in ((1, "Alpha Lab", 1), (2, "Beta Lab", 5)):
            conn.execute(
                "INSERT INTO organizations (id,name,created_by,created_at) VALUES (%s,%s,%s,%s)",
                (org_id, name, creator, SEED_TIME),
            )
        for user_id, _ in USERS:
            conn.execute(
                "INSERT INTO organization_memberships VALUES (%s,%s)",
                (2 if user_id == 5 else 1, user_id),
            )
        for project_id, org_id, name, owner in (
            (1, 1, "Alpha Collaboration", 1),
            (2, 1, "Alpha Separate Project", 7),
            (3, 2, "Beta Private Project", 5),
        ):
            conn.execute(
                """INSERT INTO projects (id,organization_id,name,created_by,created_at)
                            VALUES (%s,%s,%s,%s,%s)""",
                (project_id, org_id, name, owner, SEED_TIME),
            )
            conn.execute(
                "INSERT INTO project_memberships VALUES (%s,%s,%s,'owner')",
                (org_id, project_id, owner),
            )
            conn.execute(
                """INSERT INTO tasks
                         (id,organization_id,project_id,title,created_by,created_at,updated_at)
                         VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (
                    project_id,
                    org_id,
                    project_id,
                    f"Synthetic task {project_id}",
                    owner,
                    SEED_TIME,
                    SEED_TIME,
                ),
            )
        conn.execute("INSERT INTO project_memberships VALUES (1,1,2,'editor'), (1,1,3,'viewer')")
        for table in ("users", "organizations", "projects", "tasks"):
            conn.execute(
                sql.SQL("SELECT setval(pg_get_serial_sequence(%s, 'id'), max(id)) FROM {}").format(
                    sql.Identifier(table)
                ),
                (table,),
            )
