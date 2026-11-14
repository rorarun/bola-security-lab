import pytest

from bola_lab.auth import token_digest, verify_password
from bola_lab.db import connect

pytestmark = pytest.mark.integration
CREDS = {"email": "student@example.test", "password": "Long-Synthetic-Password!"}


def register_and_login(client):
    registered = client.post("/auth/register", json=CREDS)
    assert registered.status_code == 201
    token_response = client.post("/auth/token", json=CREDS)
    assert token_response.status_code == 200
    return registered.json(), token_response.json()


def test_registration_login_me_and_hash_storage(client, empty_database):
    user, issued = register_and_login(client)
    assert set(user) == {"id", "email"}
    assert issued["token_type"] == "bearer"
    assert issued["expires_in"] == 900
    token = issued["access_token"]
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == user
    assert response.headers["cache-control"] == "no-store"
    with connect(empty_database) as conn:
        stored = conn.execute("SELECT * FROM users WHERE id = %s", (user["id"],)).fetchone()
        session = conn.execute("SELECT * FROM auth_sessions").fetchone()
    assert stored["password_hash"].startswith("$argon2id$")
    assert verify_password(stored["password_hash"], CREDS["password"])
    assert CREDS["password"] not in stored["password_hash"]
    assert session["token_digest"] == token_digest(token)
    assert token not in str(session)
    assert (session["expires_at"] - session["created_at"]).total_seconds() == 900


def test_logout_revokes_only_current_session(client, empty_database):
    _, first = register_and_login(client)
    second = client.post("/auth/token", json=CREDS).json()
    headers = {"Authorization": f"Bearer {first['access_token']}"}
    assert first["access_token"] != second["access_token"]
    assert client.delete("/auth/token", headers=headers).status_code == 204
    assert client.get("/users/me", headers=headers).status_code == 401
    assert (
        client.get(
            "/users/me", headers={"Authorization": f"Bearer {second['access_token']}"}
        ).status_code
        == 200
    )
    with connect(empty_database) as conn:
        rows = conn.execute("SELECT revoked_at FROM auth_sessions").fetchall()
    assert sum(row["revoked_at"] is not None for row in rows) == 1


def test_expired_token_denied(client, empty_database):
    _, issued = register_and_login(client)
    with connect(empty_database) as conn:
        conn.execute(
            "UPDATE auth_sessions SET created_at = now() - interval '20 minutes', "
            "expires_at = now() - interval '1 second'"
        )
    response = client.get(
        "/users/me", headers={"Authorization": f"Bearer {issued['access_token']}"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.parametrize(
    "header",
    [None, "Bearer invalid", "Bearer " + "A" * 43, "Basic dXNlcjpwYXNz", "Bearer " + "é" * 43],
)
def test_missing_malformed_and_unknown_tokens(client, header):
    # Non-ASCII HTTP headers cannot be encoded by HTTPX; exercise ASCII malformed cases over HTTP.
    if header and "é" in header:
        from bola_lab.auth import TOKEN_PATTERN

        assert not TOKEN_PATTERN.fullmatch(header.removeprefix("Bearer "))
        return
    response = client.get("/users/me", headers={"Authorization": header} if header else {})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.parametrize(
    "email,password,expected_status",
    [
        (CREDS["email"], "Wrong-Synthetic-Password!", 401),
        ("unknown@example.test", CREDS["password"], 401),
        ("' OR 1=1 --@example.test", CREDS["password"], 422),
    ],
    ids=["wrong-password", "unknown-account", "invalid-email"],
)
def test_bad_login_does_not_issue_session(client, empty_database, email, password, expected_status):
    client.post("/auth/register", json=CREDS)
    response = client.post("/auth/token", json={"email": email, "password": password})
    # Invalid email syntax is rejected at validation; a valid unknown address gets the same 401.
    assert response.status_code == expected_status
    with connect(empty_database) as conn:
        assert conn.execute("SELECT count(*) AS n FROM auth_sessions").fetchone()["n"] == 0
        assert conn.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 1


def test_email_normalization_and_duplicate_conflict(client, empty_database):
    response = client.post("/auth/register", json=CREDS | {"email": "  STUDENT@EXAMPLE.TEST  "})
    assert response.status_code == 201
    assert response.json()["email"] == CREDS["email"]
    assert client.post("/auth/register", json=CREDS).status_code == 409
    with connect(empty_database) as conn:
        assert conn.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 1


@pytest.mark.parametrize(
    "body",
    [
        CREDS | {"password": "short"},
        CREDS | {"password": "a" * 129},
        CREDS | {"email": "not-an-email"},
        CREDS | {"role": "owner"},
        CREDS | {"organization_id": 1},
    ],
)
def test_invalid_registration_rejected_without_echoing_password(client, empty_database, body):
    response = client.post("/auth/register", json=body)
    assert response.status_code == 422
    assert body["password"] not in response.text
    assert '"input"' not in response.text
    with connect(empty_database) as conn:
        assert conn.execute("SELECT count(*) AS n FROM users").fetchone()["n"] == 0


def test_health_and_only_m1_endpoints(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    paths = set(client.get("/openapi.json").json()["paths"])
    assert paths == {"/health/live", "/health/ready", "/auth/register", "/auth/token", "/users/me"}
    assert client.get("/organizations/1/projects/1/tasks/1").status_code == 404
