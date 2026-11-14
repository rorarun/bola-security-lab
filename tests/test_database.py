from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

from bola_lab.config import Settings
from bola_lab.db import connect
from bola_lab.main import create_app
from bola_lab.migrations import MIGRATIONS, migrate, verify_schema
from bola_lab.seed import SEED_PASSWORD, seed

pytestmark = pytest.mark.integration


def test_migrations_are_repeatable_and_match_checksums(empty_database):
    migrate(empty_database)
    migrate(empty_database)
    verify_schema(empty_database)
    with connect(empty_database) as conn:
        assert conn.execute("SELECT count(*) AS n FROM schema_migrations").fetchone()["n"] == 1


def test_modified_migration_rejected(empty_database, tmp_path):
    for path in MIGRATIONS.glob("*.sql"):
        (tmp_path / path.name).write_text(path.read_text() + "\n-- tampered\n")
    with pytest.raises(RuntimeError, match="modified"):
        migrate(empty_database, tmp_path)
    verify_schema(empty_database)


def test_failed_migration_rolls_back_schema_and_history(empty_database, tmp_path):
    for path in MIGRATIONS.glob("*.sql"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    (tmp_path / "002_invalid.sql").write_text(
        "CREATE TABLE rollback_probe (id integer); SELECT no_such_function();"
    )
    from psycopg.errors import UndefinedFunction

    with pytest.raises(UndefinedFunction):
        migrate(empty_database, tmp_path)
    with connect(empty_database) as conn:
        assert (
            conn.execute("SELECT to_regclass('rollback_probe') AS probe").fetchone()["probe"]
            is None
        )
        assert conn.execute("SELECT count(*) AS n FROM schema_migrations").fetchone()["n"] == 1


def test_seed_identity_content_and_login(seeded_database):
    with connect(seeded_database) as conn:
        assert conn.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 7
        assert conn.execute("SELECT count(*) AS n FROM organizations").fetchone()["n"] == 2
        assert conn.execute("SELECT count(*) AS n FROM tasks").fetchone()["n"] == 3
        owners = conn.execute(
            "SELECT project_id, user_id FROM project_memberships "
            "WHERE role='owner' ORDER BY project_id"
        ).fetchall()
        assert owners == [
            {"project_id": 1, "user_id": 1},
            {"project_id": 2, "user_id": 7},
            {"project_id": 3, "user_id": 5},
        ]
        assert (
            conn.execute(
                "SELECT count(*) AS n FROM project_memberships WHERE user_id IN (4,6)"
            ).fetchone()["n"]
            == 0
        )
    with TestClient(create_app(seeded_database)) as client:
        issued = client.post(
            "/auth/token", json={"email": "owner@alpha.example", "password": SEED_PASSWORD}
        )
        assert issued.status_code == 200
        me = client.get(
            "/users/me", headers={"Authorization": f"Bearer {issued.json()['access_token']}"}
        )
        assert me.json() == {"id": 1, "email": "owner@alpha.example"}


def snapshot(settings):
    with connect(settings) as conn:
        return {
            table: conn.execute(query).fetchall()
            for table, query in {
                "users": "SELECT id,email,created_at FROM users ORDER BY id",
                "organizations": "SELECT * FROM organizations ORDER BY id",
                "projects": "SELECT * FROM projects ORDER BY id",
                "memberships": "SELECT * FROM project_memberships ORDER BY project_id,user_id",
                "tasks": "SELECT * FROM tasks ORDER BY id",
            }.items()
        }


def test_seed_reset_is_deterministic_and_does_not_reuse_ids(seeded_database):
    lab = Settings(database_url=seeded_database.database_url, environment="lab", lab_opt_in=True)
    before = snapshot(lab)
    with pytest.raises(ValueError, match="not empty"):
        seed(lab)
    seed(lab, reset=True)
    assert snapshot(lab) == before
    with connect(lab) as conn:
        added = conn.execute(
            "INSERT INTO users (email,password_hash) VALUES (%s,%s) RETURNING id",
            ("new@example.test", "not-a-real-hash"),
        ).fetchone()
    assert added["id"] == 8


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO tasks (organization_id,project_id,title,created_by) VALUES (2,1,'Mismatch',1)",
        "INSERT INTO project_memberships VALUES (1,1,5,'viewer')",
        "INSERT INTO project_memberships VALUES (2,1,5,'viewer')",
    ],
)
def test_tenant_relationship_constraints(seeded_database, statement):
    before = snapshot(seeded_database)
    with pytest.raises(ForeignKeyViolation), connect(seeded_database) as conn:
        conn.execute(statement)
    assert snapshot(seeded_database) == before


def test_ownerless_project_cannot_commit(seeded_database):
    with pytest.raises(CheckViolation), connect(seeded_database) as conn:
        conn.execute(
            "INSERT INTO projects (organization_id,name,created_by) VALUES (1,'Ownerless',1)"
        )
    with connect(seeded_database) as conn:
        assert conn.execute("SELECT count(*) AS n FROM projects").fetchone()["n"] == 3


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE project_memberships SET role='editor' WHERE project_id=1 AND user_id=1",
        "UPDATE project_memberships SET user_id=4 WHERE project_id=1 AND user_id=1",
        "DELETE FROM project_memberships WHERE project_id=1 AND user_id=1",
        "DELETE FROM organization_memberships WHERE organization_id=1 AND user_id=1",
    ],
)
def test_owner_cannot_be_removed_or_transferred(seeded_database, statement):
    before = snapshot(seeded_database)
    with pytest.raises(CheckViolation), connect(seeded_database) as conn:
        conn.execute(statement)
    assert snapshot(seeded_database) == before


def test_second_owner_rejected(seeded_database):
    with pytest.raises(UniqueViolation), connect(seeded_database) as conn:
        conn.execute("INSERT INTO project_memberships VALUES (1,1,4,'owner')")


def test_invalid_role_rejected(seeded_database):
    with pytest.raises(CheckViolation), connect(seeded_database) as conn:
        conn.execute("INSERT INTO project_memberships VALUES (1,1,4,'admin')")


def test_project_delete_cascades_only_its_children(seeded_database):
    with connect(seeded_database) as conn:
        conn.execute("DELETE FROM projects WHERE id = 1")
    with connect(seeded_database) as conn:
        assert conn.execute("SELECT id FROM projects ORDER BY id").fetchall() == [
            {"id": 2},
            {"id": 3},
        ]
        assert conn.execute("SELECT id FROM tasks ORDER BY id").fetchall() == [{"id": 2}, {"id": 3}]
        assert (
            conn.execute(
                "SELECT count(*) AS n FROM project_memberships WHERE project_id=1"
            ).fetchone()["n"]
            == 0
        )


def test_schema_mismatch_rejects_startup(empty_database):
    try:
        with connect(empty_database) as conn:
            conn.execute("UPDATE schema_migrations SET sha256 = 'wrong'")
        with (
            pytest.raises(RuntimeError, match="migrations do not match"),
            TestClient(create_app(empty_database)),
        ):
            pass
    finally:
        import hashlib

        with connect(empty_database) as conn:
            path = Path(MIGRATIONS) / "001_foundation.sql"
            conn.execute(
                "UPDATE schema_migrations SET sha256=%s",
                (hashlib.sha256(path.read_bytes()).hexdigest(),),
            )
