import os

import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict

from bola_lab.config import Settings
from bola_lab.db import connect
from bola_lab.main import create_app
from bola_lab.migrations import migrate
from bola_lab.seed import seed


@pytest.fixture(scope="session")
def database_settings():
    url = os.environ.get("BOLA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set BOLA_TEST_DATABASE_URL to run real PostgreSQL integration checks")
    parameters = conninfo_to_dict(url)
    if not parameters.get("dbname", "").endswith("_test") or parameters.get("host") not in {
        "127.0.0.1",
        "localhost",
        "::1",
        "db",
    }:
        pytest.fail("Destructive tests require a local database whose name ends in _test")
    settings = Settings(database_url=url, environment="test")
    migrate(settings)
    return settings


@pytest.fixture
def empty_database(database_settings):
    with connect(database_settings) as conn:
        conn.execute(
            "TRUNCATE users, organizations, organization_memberships, projects, "
            "project_memberships, tasks, auth_sessions RESTART IDENTITY CASCADE"
        )
    return database_settings


@pytest.fixture
def seeded_database(empty_database):
    seed(Settings(database_url=empty_database.database_url, environment="lab", lab_opt_in=True))
    return empty_database


@pytest.fixture
def client(empty_database):
    with TestClient(create_app(empty_database)) as client:
        yield client


@pytest.fixture
def resource_client(seeded_database):
    with TestClient(create_app(seeded_database)) as client:
        yield client


@pytest.fixture
def actor(resource_client):
    from bola_lab.seed import SEED_PASSWORD, USERS

    tokens = {}

    def headers(user_id):
        if user_id not in tokens:
            response = resource_client.post(
                "/auth/token",
                json={
                    "email": dict(USERS)[user_id],
                    "password": SEED_PASSWORD,
                },
            )
            assert response.status_code == 200
            tokens[user_id] = response.json()["access_token"]
        return {"Authorization": f"Bearer {tokens[user_id]}"}

    return headers
