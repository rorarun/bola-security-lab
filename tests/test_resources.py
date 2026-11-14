"""Independent matrix expectations and persisted-state assertions; no production policy imports."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from psycopg import sql

from bola_lab.config import Settings
from bola_lab.db import connect
from bola_lab.local_admin import add_organization_member
from bola_lab.main import create_app

pytestmark = pytest.mark.integration
PROJECT = "/organizations/1/projects/1"
TASKS = PROJECT + "/tasks"
MEMBERS = PROJECT + "/memberships"


def domain_state(settings):
    with connect(settings) as conn:
        return {
            table: conn.execute(
                sql.SQL("SELECT * FROM {} ORDER BY 1,2").format(sql.Identifier(table))
            ).fetchall()
            for table in (
                "organizations",
                "organization_memberships",
                "projects",
                "project_memberships",
                "tasks",
            )
        }


OPERATIONS = [
    ("GET", "", None),
    ("PATCH", "", {"name": "Unauthorized"}),
    ("DELETE", "", None),
    ("GET", "/memberships", None),
    ("POST", "/memberships", {"user_id": 4, "role": "editor"}),
    ("PATCH", "/memberships/2", {"role": "viewer"}),
    ("DELETE", "/memberships/2", None),
    ("GET", "/tasks", None),
    ("GET", "/tasks/1", None),
    ("POST", "/tasks", {"title": "Unauthorized"}),
    ("PATCH", "/tasks/1", {"title": "Unauthorized", "status": "done"}),
    ("DELETE", "/tasks/1", None),
]
OPERATION_IDS = [
    "project-read",
    "project-update",
    "project-delete",
    "members-list",
    "member-add",
    "member-update",
    "member-revoke",
    "tasks-list",
    "task-read",
    "task-create",
    "task-update",
    "task-delete",
]


@pytest.mark.parametrize(
    "user_id", [4, 5, 7], ids=["same-org-outsider", "cross-org", "other-project-owner"]
)
@pytest.mark.parametrize("method,suffix,body", OPERATIONS, ids=OPERATION_IDS)
def test_outsiders_denied_without_domain_changes(
    resource_client, actor, seeded_database, user_id, method, suffix, body
):
    headers = actor(user_id)
    before = domain_state(seeded_database)
    response = resource_client.request(method, PROJECT + suffix, headers=headers, json=body)
    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found"}
    assert domain_state(seeded_database) == before


@pytest.mark.parametrize("method,suffix,body", OPERATIONS, ids=OPERATION_IDS)
def test_resource_operations_require_authentication(
    resource_client, seeded_database, method, suffix, body
):
    before = domain_state(seeded_database)
    response = resource_client.request(method, PROJECT + suffix, json=body)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}
    assert domain_state(seeded_database) == before


@pytest.mark.parametrize(
    "user_id,expected_org,expected_projects",
    [
        (1, 1, [1]),
        (2, 1, [1]),
        (3, 1, [1]),
        (4, 1, []),
        (5, 2, [3]),
        (7, 1, [2]),
    ],
)
def test_organization_and_project_lists_are_exact(
    resource_client, actor, user_id, expected_org, expected_projects
):
    headers = actor(user_id)
    response = resource_client.get("/organizations", headers=headers)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [expected_org]
    assert response.json()[0]["name"] == ("Alpha Lab" if expected_org == 1 else "Beta Lab")
    detail = resource_client.get(f"/organizations/{expected_org}", headers=headers)
    assert detail.status_code == 200 and detail.json() == response.json()[0]
    projects = resource_client.get(f"/organizations/{expected_org}/projects", headers=headers)
    assert projects.status_code == 200
    assert [row["id"] for row in projects.json()] == expected_projects
    assert all(row["organization_id"] == expected_org for row in projects.json())


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/organizations/2", None),
        ("GET", "/organizations/2/projects", None),
        ("POST", "/organizations/2/projects", {"name": "Cross tenant"}),
        ("GET", "/organizations/99999", None),
    ],
)
def test_organization_boundary(resource_client, actor, seeded_database, method, path, body):
    before = domain_state(seeded_database)
    response = resource_client.request(method, path, headers=actor(1), json=body)
    assert response.status_code == 404 and response.json() == {"detail": "Resource not found"}
    assert domain_state(seeded_database) == before


def test_organization_and_project_creation_are_atomic(resource_client, actor, seeded_database):
    created = resource_client.post(
        "/organizations", headers=actor(4), json={"name": " New Synthetic Org "}
    )
    assert created.status_code == 201
    org = created.json()
    assert org["name"] == "New Synthetic Org" and org["created_by"] == 4
    new_project = resource_client.post(
        f"/organizations/{org['id']}/projects",
        headers=actor(4),
        json={"name": "New Project", "description": "Synthetic"},
    )
    assert new_project.status_code == 201
    project = new_project.json()
    assert project["organization_id"] == org["id"] and project["created_by"] == 4
    with connect(seeded_database) as conn:
        assert conn.execute(
            "SELECT * FROM organization_memberships WHERE organization_id=%s", (org["id"],)
        ).fetchall() == [{"organization_id": org["id"], "user_id": 4}]
        assert conn.execute(
            "SELECT * FROM project_memberships WHERE project_id=%s", (project["id"],)
        ).fetchall() == [
            {
                "organization_id": org["id"],
                "project_id": project["id"],
                "user_id": 4,
                "role": "owner",
            }
        ]
    empty = resource_client.get(
        f"/organizations/{org['id']}/projects/{project['id']}/tasks", headers=actor(4)
    )
    assert empty.status_code == 200 and empty.json() == []


def test_org_member_can_create_project_without_access_to_other_projects(
    resource_client, actor, seeded_database
):
    response = resource_client.post(
        "/organizations/1/projects", headers=actor(4), json={"name": "Own project"}
    )
    assert response.status_code == 201 and response.json()["created_by"] == 4
    project_id = response.json()["id"]
    visible = resource_client.get("/organizations/1/projects", headers=actor(4))
    assert [row["id"] for row in visible.json()] == [project_id]
    assert resource_client.get(PROJECT, headers=actor(4)).status_code == 404
    with connect(seeded_database) as conn:
        assert conn.execute(
            "SELECT user_id,role FROM project_memberships WHERE project_id=%s", (project_id,)
        ).fetchall() == [{"user_id": 4, "role": "owner"}]


@pytest.mark.parametrize("user_id", [1, 2, 3], ids=["owner", "editor", "viewer"])
def test_all_members_can_read_only_their_project_tasks(resource_client, actor, user_id):
    headers = actor(user_id)
    project = resource_client.get(PROJECT, headers=headers)
    assert project.status_code == 200
    assert project.json()["id"] == 1 and project.json()["organization_id"] == 1
    assert set(project.json()) == {
        "id",
        "name",
        "description",
        "organization_id",
        "created_by",
        "created_at",
    }
    tasks = resource_client.get(TASKS, headers=headers)
    assert tasks.status_code == 200 and [row["id"] for row in tasks.json()] == [1]
    assert tasks.json()[0]["title"] == "Synthetic task 1"
    detail = resource_client.get(TASKS + "/1", headers=headers)
    assert detail.status_code == 200 and detail.json() == tasks.json()[0]
    assert detail.json()["project_id"] == detail.json()["organization_id"] == 1


@pytest.mark.parametrize("user_id", [1, 2], ids=["owner", "editor"])
def test_task_create_and_update_persist_exact_values(
    resource_client, actor, seeded_database, user_id
):
    headers = actor(user_id)
    response = resource_client.post(
        TASKS,
        headers=headers,
        json={"title": " New task ", "description": "Initial", "status": "in_progress"},
    )
    assert response.status_code == 201
    task = response.json()
    assert task["title"] == "New task" and task["created_by"] == user_id
    assert task["project_id"] == task["organization_id"] == 1
    updated = resource_client.patch(
        TASKS + f"/{task['id']}",
        headers=headers,
        json={"title": "Updated", "description": "", "status": "done"},
    )
    assert updated.status_code == 200
    assert {
        key: updated.json()[key] for key in ("title", "description", "status", "created_by")
    } == {"title": "Updated", "description": "", "status": "done", "created_by": user_id}
    with connect(seeded_database) as conn:
        stored = conn.execute("SELECT * FROM tasks WHERE id=%s", (task["id"],)).fetchone()
    assert (stored["title"], stored["description"], stored["status"], stored["created_by"]) == (
        "Updated",
        "",
        "done",
        user_id,
    )
    assert stored["organization_id"] == stored["project_id"] == 1
    assert stored["updated_at"] >= stored["created_at"]


def test_editor_can_update_task_created_by_owner(resource_client, actor, seeded_database):
    response = resource_client.patch(TASKS + "/1", headers=actor(2), json={"status": "done"})
    assert response.status_code == 200 and response.json()["created_by"] == 1
    assert response.json()["title"] == "Synthetic task 1"
    with connect(seeded_database) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=1").fetchone()
        assert row["status"] == "done" and row["created_by"] == 1


ROLE_DENIALS = [
    (3, "POST", "/tasks", {"title": "Forbidden"}),
    (3, "PATCH", "/tasks/1", {"title": "Forbidden"}),
    (3, "DELETE", "/tasks/1", None),
    (2, "DELETE", "/tasks/1", None),
] + [
    (user_id, method, suffix, body)
    for user_id in (2, 3)
    for method, suffix, body in OPERATIONS[:7]
    if method != "GET" or suffix == "/memberships"
]


@pytest.mark.parametrize("user_id,method,suffix,body", ROLE_DENIALS)
def test_role_boundaries_preserve_state(
    resource_client, actor, seeded_database, user_id, method, suffix, body
):
    before = domain_state(seeded_database)
    response = resource_client.request(method, PROJECT + suffix, headers=actor(user_id), json=body)
    assert response.status_code == 403 and response.json() == {
        "detail": "Insufficient project role"
    }
    assert domain_state(seeded_database) == before


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize(
    "task_id", [2, 3, 99999], ids=["other-project", "other-organization", "absent"]
)
def test_task_identifier_mismatch_or_absence_never_mutates_target(
    resource_client, actor, seeded_database, method, task_id
):
    before = domain_state(seeded_database)
    response = resource_client.request(
        method,
        f"{TASKS}/{task_id}",
        headers=actor(1),
        json={"title": "Forbidden"} if method == "PATCH" else None,
    )
    assert response.status_code == 404 and response.json() == {"detail": "Resource not found"}
    assert domain_state(seeded_database) == before


@pytest.mark.parametrize("method,suffix,body", OPERATIONS, ids=OPERATION_IDS)
def test_wrong_organization_project_pair(
    resource_client, actor, seeded_database, method, suffix, body
):
    # Caller belongs to BOTH organizations and owns project 1: denying this request
    # must depend on the actual parent relationship, not incidental nonmembership.
    add_organization_member(
        Settings(database_url=seeded_database.database_url, environment="lab", lab_opt_in=True),
        2,
        1,
    )
    assert resource_client.get("/organizations/2", headers=actor(1)).status_code == 200
    before = domain_state(seeded_database)
    path = "/organizations/2/projects/1" + suffix
    response = resource_client.request(method, path, headers=actor(1), json=body)
    assert response.status_code == 404
    assert domain_state(seeded_database) == before


def test_owner_updates_and_deletes_only_owned_project(resource_client, actor, seeded_database):
    before = domain_state(seeded_database)
    response = resource_client.patch(
        PROJECT, headers=actor(1), json={"name": "Renamed", "description": "Changed"}
    )
    assert response.status_code == 200 and response.json()["name"] == "Renamed"
    with connect(seeded_database) as conn:
        stored = conn.execute(
            "SELECT name,description,created_by FROM projects WHERE id=1"
        ).fetchone()
    assert stored == {"name": "Renamed", "description": "Changed", "created_by": 1}
    deleted = resource_client.delete(PROJECT, headers=actor(1))
    assert deleted.status_code == 204 and deleted.content == b""
    after = domain_state(seeded_database)
    assert after["projects"] == [row for row in before["projects"] if row["id"] != 1]
    assert after["tasks"] == [row for row in before["tasks"] if row["project_id"] != 1]
    assert after["project_memberships"] == [
        row for row in before["project_memberships"] if row["project_id"] != 1
    ]
    assert after["organization_memberships"] == before["organization_memberships"]


def test_owner_deletes_task_without_touching_other_tasks(resource_client, actor, seeded_database):
    before = domain_state(seeded_database)
    response = resource_client.delete(TASKS + "/1", headers=actor(1))
    assert response.status_code == 204 and response.content == b""
    after = domain_state(seeded_database)
    assert after["tasks"] == [row for row in before["tasks"] if row["id"] != 1]
    assert after["projects"] == before["projects"]


def test_membership_lifecycle_uses_current_roles_and_same_unexpired_tokens(
    resource_client, actor, seeded_database
):
    owner, member = actor(1), actor(6)
    initial = resource_client.get(TASKS + "/1", headers=member)
    assert initial.status_code == 404
    added = resource_client.post(MEMBERS, headers=owner, json={"user_id": 6, "role": "editor"})
    assert added.status_code == 201 and added.json() == {
        "organization_id": 1,
        "project_id": 1,
        "user_id": 6,
        "role": "editor",
    }
    assert (
        resource_client.patch(
            TASKS + "/1", headers=member, json={"status": "in_progress"}
        ).status_code
        == 200
    )
    changed = resource_client.patch(MEMBERS + "/6", headers=owner, json={"role": "viewer"})
    assert changed.status_code == 200 and changed.json()["role"] == "viewer"
    before = domain_state(seeded_database)
    assert (
        resource_client.patch(TASKS + "/1", headers=member, json={"status": "done"}).status_code
        == 403
    )
    assert domain_state(seeded_database) == before
    assert resource_client.get(TASKS + "/1", headers=member).json()["status"] == "in_progress"
    assert resource_client.delete(MEMBERS + "/6", headers=owner).status_code == 204
    before = domain_state(seeded_database)
    for method, path, body in (
        ("GET", TASKS + "/1", None),
        ("POST", TASKS, {"title": "Forbidden"}),
        ("PATCH", TASKS + "/1", {"status": "done"}),
        ("DELETE", TASKS + "/1", None),
    ):
        assert resource_client.request(method, path, headers=member, json=body).status_code == 404
    assert domain_state(seeded_database) == before
    assert resource_client.get("/users/me", headers=member).status_code == 200
    members = resource_client.get(MEMBERS, headers=owner)
    assert members.status_code == 200
    assert [(row["user_id"], row["role"]) for row in members.json()] == [
        (1, "owner"),
        (2, "editor"),
        (3, "viewer"),
    ]
    with connect(seeded_database) as conn:
        assert (
            conn.execute(
                "SELECT 1 FROM project_memberships WHERE project_id=1 AND user_id=6"
            ).fetchone()
            is None
        )
        assert (
            conn.execute("SELECT status FROM tasks WHERE id=1").fetchone()["status"]
            == "in_progress"
        )


@pytest.mark.parametrize(
    "method,path,body,expected",
    [
        ("PATCH", MEMBERS + "/1", {"role": "viewer"}, 409),
        ("DELETE", MEMBERS + "/1", None, 409),
        ("POST", MEMBERS, {"user_id": 4, "role": "owner"}, 422),
        ("PATCH", MEMBERS + "/2", {"role": "owner"}, 422),
        ("POST", MEMBERS, {"user_id": 2, "role": "viewer"}, 409),
        ("POST", MEMBERS, {"user_id": 5, "role": "viewer"}, 404),
        ("POST", MEMBERS, {"user_id": 99999, "role": "viewer"}, 404),
        ("PATCH", MEMBERS + "/99999", {"role": "editor"}, 404),
        ("DELETE", MEMBERS + "/99999", None, 404),
    ],
)
def test_invalid_membership_operations_are_atomic(
    resource_client, actor, seeded_database, method, path, body, expected
):
    before = domain_state(seeded_database)
    response = resource_client.request(method, path, headers=actor(1), json=body)
    assert response.status_code == expected
    assert domain_state(seeded_database) == before


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "/organizations", {"name": "Bad", "created_by": 5}),
        ("POST", "/organizations/1/projects", {"name": "Bad", "created_by": 5}),
        ("POST", "/organizations/1/projects", {"name": "Bad", "organization_id": 2}),
        ("PATCH", PROJECT, {"created_by": 5}),
        ("PATCH", PROJECT, {"organization_id": 2}),
        ("POST", TASKS, {"title": "Bad", "created_by": 5}),
        ("POST", TASKS, {"title": "Bad", "project_id": 2}),
        ("PATCH", TASKS + "/1", {"organization_id": 2}),
        ("PATCH", TASKS + "/1", {"project_id": 2}),
        ("PATCH", TASKS + "/1", {"created_by": 5}),
        ("PATCH", TASKS + "/1", {"id": 2}),
        ("PATCH", MEMBERS + "/2", {"role": "viewer", "user_id": 5}),
    ],
)
def test_client_cannot_reassign_identity_tenant_or_ownership(
    resource_client, actor, seeded_database, method, path, body
):
    before = domain_state(seeded_database)
    assert resource_client.request(method, path, headers=actor(1), json=body).status_code == 422
    assert domain_state(seeded_database) == before


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("PATCH", TASKS + "/1", {}),
        ("PATCH", TASKS + "/1", {"title": None}),
        ("PATCH", TASKS + "/1", {"title": "   "}),
        ("PATCH", TASKS + "/1", {"status": "unknown"}),
        ("PATCH", TASKS + "/1", {"description": "x" * 4001}),
        ("PATCH", PROJECT, {}),
        ("PATCH", PROJECT, {"name": None}),
        ("POST", TASKS, {"title": "x" * 201}),
        ("POST", "/organizations", {"name": "   "}),
        ("GET", "/organizations/9223372036854775808", None),
    ],
)
def test_invalid_resource_inputs_leave_database_unchanged(
    resource_client, actor, seeded_database, method, path, body
):
    before = domain_state(seeded_database)
    assert resource_client.request(method, path, headers=actor(1), json=body).status_code == 422
    assert domain_state(seeded_database) == before


@pytest.mark.parametrize(
    "hook,path,body",
    [
        ("create_organization", "/organizations", {"name": "Rollback"}),
        ("create_project", "/organizations/1/projects", {"name": "Rollback"}),
        ("create_task", TASKS, {"title": "Rollback"}),
    ],
)
def test_mid_operation_failure_rolls_back_all_rows(
    resource_client, actor, seeded_database, monkeypatch, hook, path, body
):
    from bola_lab import repository

    original = getattr(repository, hook)

    def fail_after_insert(*args, **kwargs):
        original(*args, **kwargs)
        raise HTTPException(409, "Injected synthetic transaction failure")

    monkeypatch.setattr(repository, hook, fail_after_insert)
    before = domain_state(seeded_database)
    response = resource_client.post(path, headers=actor(1), json=body)
    assert response.status_code == 409
    assert domain_state(seeded_database) == before


def test_controlled_organization_provisioning(seeded_database):
    lab = Settings(database_url=seeded_database.database_url, environment="lab", lab_opt_in=True)
    add_organization_member(lab, 2, 4)
    with connect(lab) as conn:
        assert conn.execute(
            "SELECT 1 FROM organization_memberships WHERE organization_id=2 AND user_id=4"
        ).fetchone()
        assert (
            conn.execute(
                "SELECT 1 FROM project_memberships WHERE project_id=3 AND user_id=4"
            ).fetchone()
            is None
        )
    before = domain_state(lab)
    with pytest.raises(ValueError, match="already belongs"):
        add_organization_member(lab, 2, 4)
    with pytest.raises(ValueError, match="does not exist"):
        add_organization_member(lab, 99999, 4)
    with pytest.raises(ValueError, match="explicit lab_opt_in"):
        add_organization_member(seeded_database, 2, 6)
    assert domain_state(lab) == before


def test_explicit_endpoint_configuration_uses_same_secure_behavior(seeded_database):
    settings = Settings(
        database_url=seeded_database.database_url,
        authorization_mode="endpoint",
        environment="lab",
        lab_opt_in=True,
    )
    with TestClient(create_app(settings)) as client:
        assert client.app.state.authorization_implementation == "endpoint-specific"
        from bola_lab.seed import SEED_PASSWORD

        issued = client.post(
            "/auth/token", json={"email": "viewer@alpha.example", "password": SEED_PASSWORD}
        )
        assert issued.status_code == 200
        headers = {"Authorization": f"Bearer {issued.json()['access_token']}"}
        assert client.get(TASKS + "/1", headers=headers).json()["id"] == 1
        before = domain_state(seeded_database)
        assert client.delete(TASKS + "/1", headers=headers).status_code == 403
        assert domain_state(seeded_database) == before


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "/organizations", {"name": "Forbidden"}),
        ("GET", "/organizations", None),
        ("GET", "/organizations/1", None),
        ("POST", "/organizations/1/projects", {"name": "Forbidden"}),
        ("GET", "/organizations/1/projects", None),
    ],
)
def test_collections_also_require_authentication(
    resource_client, seeded_database, method, path, body
):
    before = domain_state(seeded_database)
    assert resource_client.request(method, path, json=body).status_code == 401
    assert domain_state(seeded_database) == before


def test_promoted_viewer_can_collaborate_with_existing_token(
    resource_client, actor, seeded_database
):
    viewer = actor(3)
    assert (
        resource_client.post(TASKS, headers=viewer, json={"title": "Not yet allowed"}).status_code
        == 403
    )
    updated = resource_client.patch(MEMBERS + "/3", headers=actor(1), json={"role": "editor"})
    assert updated.status_code == 200 and updated.json()["role"] == "editor"
    created = resource_client.post(TASKS, headers=viewer, json={"title": "Allowed after promotion"})
    assert created.status_code == 201 and created.json()["created_by"] == 3
    with connect(seeded_database) as conn:
        row = conn.execute(
            "SELECT title,created_by FROM tasks WHERE id=%s", (created.json()["id"],)
        ).fetchone()
    assert row == {"title": "Allowed after promotion", "created_by": 3}


def test_local_cli_provisions_only_an_organization_membership(seeded_database):
    import os
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bola_lab.cli",
            "organization-member",
            "--organization-id",
            "2",
            "--user-id",
            "4",
        ],
        env={
            **os.environ,
            "BOLA_DATABASE_URL": seeded_database.database_url.get_secret_value(),
            "BOLA_ENVIRONMENT": "lab",
            "BOLA_LAB_OPT_IN": "true",
            "BOLA_AUTHORIZATION_MODE": "hardened",
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert (
        result.returncode == 0
        and result.stdout.strip() == "Synthetic organization membership added."
    )
    with connect(seeded_database) as conn:
        assert conn.execute(
            "SELECT 1 FROM organization_memberships WHERE organization_id=2 AND user_id=4"
        ).fetchone()
        assert (
            conn.execute(
                "SELECT 1 FROM project_memberships WHERE organization_id=2 AND user_id=4"
            ).fetchone()
            is None
        )
