"""Harness-owned loopback HTTP server and dedicated synthetic PostgreSQL experiment."""

import argparse
import base64
import importlib.metadata
import io
import json
import os
import platform
import re
import socket
import subprocess
import sys
import tarfile
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from bola_lab.auth import TOKEN_PATTERN, token_digest
from bola_lab.config import Settings
from bola_lab.db import connect
from bola_lab.evaluation.checks import KEYS, sort_state
from bola_lab.evaluation.models import (
    PACKAGE,
    ROOT,
    canonical,
    digest,
    read_frozen,
    sanitize,
    scenarios,
    source_hashes,
)
from bola_lab.migrations import migrate
from bola_lab.seed import SEED_PASSWORD, seed

DATABASE = "bola_lab_evaluation_test"


def now():
    return datetime.now(UTC).isoformat()


def evaluation_settings(url: str) -> Settings:
    parameters = conninfo_to_dict(url)
    if (
        parameters.get("dbname") != DATABASE
        or parameters.get("host") not in {"127.0.0.1", "::1", "localhost", "db"}
        or parameters.get("hostaddr", "127.0.0.1") not in {"127.0.0.1", "::1"}
        or parameters.get("service")
    ):
        raise ValueError("Evaluation requires the dedicated local synthetic evaluation database")
    return Settings(database_url=url, environment="test", authorization_mode="hardened")


def snapshot(settings):
    with connect(settings) as conn:
        state = {}
        for table in KEYS:
            fields = sql.SQL("id,email,created_at") if table == "users" else sql.SQL("*")
            state[table] = canonical(
                conn.execute(
                    sql.SQL("SELECT {} FROM {}").format(fields, sql.Identifier(table))
                ).fetchall()
            )
    return sort_state(state)


def sessions(settings):
    with connect(settings) as conn:
        row = conn.execute("""SELECT count(*) AS total,
            count(*) FILTER (WHERE expires_at <= now()) AS expired,
            count(*) FILTER (WHERE revoked_at IS NOT NULL) AS revoked,
            bool_and(expires_at > created_at AND expires_at-created_at <= interval '900 seconds')
                AS valid_lifetimes,
            bool_and(expires_at-created_at <= interval '900 seconds')
                FILTER (WHERE expires_at > now()) AS valid_active_lifetimes
            FROM auth_sessions""").fetchone()
    return row


@contextmanager
def live_server(settings):
    """No remote URL input, published port, ASGI mock transport, or shared application DB."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        address = f"http://127.0.0.1:{listener.getsockname()[1]}"
        environment = {
            key: value for key, value in os.environ.items() if not key.startswith("BOLA_")
        }
        environment.update(
            BOLA_DATABASE_URL=settings.database_url.get_secret_value(),
            BOLA_ENVIRONMENT="test",
            BOLA_AUTHORIZATION_MODE="hardened",
            BOLA_BIND_HOST="127.0.0.1",
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "bola_lab.main:create_app",
                "--factory",
                "--fd",
                str(listener.fileno()),
                "--no-access-log",
                "--log-level",
                "error",
            ],
            pass_fds=(listener.fileno(),),
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            with httpx.Client(
                base_url=address, timeout=3, follow_redirects=False, trust_env=False
            ) as client:
                deadline = time.monotonic() + 20
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Harness-owned API startup failed")
                    try:
                        if client.get("/health/ready").json() == {"status": "ready"}:
                            break
                    except (httpx.HTTPError, ValueError):
                        pass
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Harness-owned API readiness timed out")
                    time.sleep(0.05)
                yield client
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def reset_fixture(settings):
    seed(
        Settings(database_url=settings.database_url, environment="lab", lab_opt_in=True), reset=True
    )
    expected = sort_state(read_frozen("fixture.json")["state"])
    if snapshot(settings) != expected:
        raise ValueError("Fixture does not match frozen independent contract")
    return expected


def login(client, actor_id):
    users = read_frozen("fixture.json")["state"]["users"]
    email = next(row["email"] for row in users if row["id"] == actor_id)
    response = client.post("/auth/token", json={"email": email, "password": SEED_PASSWORD})
    body = response.json()
    if (
        response.status_code != 200
        or set(body) != {"access_token", "token_type", "expires_in"}
        or not TOKEN_PATTERN.fullmatch(body["access_token"])
        or body["token_type"] != "bearer"
        or body["expires_in"] != 900
    ):
        raise ValueError("Synthetic authentication setup failed")
    identity = client.get("/users/me", headers={"Authorization": "Bearer " + body["access_token"]})
    if identity.status_code != 200 or identity.json() != {"id": actor_id, "email": email}:
        raise ValueError("Authenticated synthetic identity does not match the fixture")
    return body["access_token"]


def prepare(spec, settings, client, tokens, base):
    expected = deepcopy(base)
    setup_evidence = []

    def http(method, path, *, body=None, expected_status, expected_body=None):
        response = client.request(
            method, path, json=body, headers={"Authorization": "Bearer " + tokens[1]}
        )
        actual = response.json() if response.content else None
        setup_evidence.append(
            {
                "method": method,
                "path": path,
                "status": response.status_code,
                "response": sanitize(actual, [SEED_PASSWORD, *tokens.values()]),
            }
        )
        if response.status_code != expected_status or (
            expected_body is not None and actual != expected_body
        ):
            raise ValueError("HTTP scenario setup did not meet independent precondition")

    for step in spec.setup:
        if step == "empty_project":
            row = dict(
                id=4,
                organization_id=1,
                name="Evaluation empty",
                description="",
                created_by=1,
                created_at="2026-11-14T12:00:00Z",
            )
            member = dict(organization_id=1, project_id=4, user_id=1, role="owner")
            with connect(settings) as conn:
                conn.execute(
                    "INSERT INTO projects "
                    "(id,organization_id,name,description,created_by,created_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (4, 1, row["name"], "", 1, row["created_at"]),
                )
                conn.execute("INSERT INTO project_memberships VALUES (1,4,1,'owner')")
            expected["projects"].append(row)
            expected["project_memberships"].append(member)
        elif step == "dual_organization":
            with connect(settings) as conn:
                conn.execute("INSERT INTO organization_memberships VALUES (2,1)")
            expected["organization_memberships"].append(dict(organization_id=2, user_id=1))
        elif step in {"downgrade_editor", "promote_viewer"}:
            user_id, role = (2, "viewer") if step == "downgrade_editor" else (3, "editor")
            http(
                "PATCH",
                f"/organizations/1/projects/1/memberships/{user_id}",
                body={"role": role},
                expected_status=200,
                expected_body=dict(organization_id=1, project_id=1, user_id=user_id, role=role),
            )
            next(
                row
                for row in expected["project_memberships"]
                if row["project_id"] == 1 and row["user_id"] == user_id
            )["role"] = role
        elif step == "grant_then_revoke":
            http(
                "POST",
                "/organizations/1/projects/1/memberships",
                body={"user_id": 6, "role": "editor"},
                expected_status=201,
                expected_body=dict(organization_id=1, project_id=1, user_id=6, role="editor"),
            )
            # Prove this very session accesses the protected object before committed revocation.
            response = client.get(
                "/organizations/1/projects/1/tasks/1",
                headers={"Authorization": "Bearer " + tokens[6]},
            )
            expected_task = next(r for r in expected["tasks"] if r["id"] == 1)
            if response.status_code != 200 or response.json() != expected_task:
                raise ValueError("Pre-revocation access was not established")
            setup_evidence.append(
                {
                    "method": "GET",
                    "path": "/organizations/1/projects/1/tasks/1",
                    "status": 200,
                    "response": response.json(),
                }
            )
            http("DELETE", "/organizations/1/projects/1/memberships/6", expected_status=204)
        elif step == "expired_token":
            with connect(settings) as conn:
                conn.execute(
                    "UPDATE auth_sessions SET created_at=now()-interval '20 minutes', "
                    "expires_at=now()-interval '1 second' WHERE token_digest=%s",
                    (token_digest(tokens[spec.actor_id]),),
                )
        elif step == "revoked_token":
            http("DELETE", "/auth/token", expected_status=204)
        elif step not in {"missing_token", "malformed_token"}:
            raise ValueError("Unknown scenario setup")
    if snapshot(settings) != sort_state(expected):
        raise ValueError("Prepared database does not match independent precondition")
    return setup_evidence


def execute(spec, settings, client, inventory_hash):
    record = {
        "scenario_id": spec.id,
        "inventory_sha256": inventory_hash,
        "actor_id": spec.actor_id,
        "request": spec.request,
        "started_at": now(),
        "finished_at": None,
        "before": None,
        "after": None,
        "response": None,
        "errors": [],
        "setup": [],
        "request_sent": False,
        "auth_session_delta": None,
        "session_evidence_ok": False,
    }
    stage = "fixture"
    tokens = {}
    issued = None
    try:
        base = reset_fixture(settings)
        stage = "authentication_setup"
        tokens = {actor: login(client, actor) for actor in range(1, 8)}
        stage = "scenario_setup"
        record["setup"] = prepare(spec, settings, client, tokens, base)
        stage = "before_evidence"
        record["before"] = snapshot(settings)
        auth_before = sessions(settings)
        record["auth_before"] = auth_before
        body = spec.request.get("body")
        token = tokens[spec.actor_id]
        headers = {"Authorization": "Bearer " + token}
        if "missing_token" in spec.setup:
            headers = {}
        if "malformed_token" in spec.setup:
            headers = {"Authorization": "Bearer invalid-synthetic-format"}
        if spec.request["path"] == "/auth/token":
            email = next(r["email"] for r in base["users"] if r["id"] == spec.actor_id)
            body = {
                "email": email,
                "password": SEED_PASSWORD if spec.id == "H1" else "Incorrect-Synthetic-Password!",
            }
        stage = "http_request"
        record["started_at"] = now()
        record["request_sent"] = True
        response = client.request(
            spec.request["method"], spec.request["path"], json=body, headers=headers
        )
        stage = "response_evidence"
        raw = response.json() if response.content else None
        if spec.id == "H1" and isinstance(raw, dict):
            record["auth_response_valid"] = set(raw) == {"access_token", "token_type", "expires_in"}
            issued = raw.get("access_token", "")
            raw = dict(
                token_issued=bool(isinstance(issued, str) and TOKEN_PATTERN.fullmatch(issued)),
                token_type=raw.get("token_type"),
                expires_in=raw.get("expires_in"),
            )
            if issued:
                tokens[0] = issued
        record["response"] = {
            "status": response.status_code,
            "body": sanitize(
                raw, [SEED_PASSWORD, "Incorrect-Synthetic-Password!", *tokens.values()]
            ),
            "headers": {
                key: response.headers[key]
                for key in ("cache-control", "www-authenticate")
                if key in response.headers
            },
        }
        if response.status_code >= 500:
            record["errors"].append({"stage": "application_response", "type": "HTTP5xx"})
    except Exception as error:
        record["errors"].append({"stage": stage, "type": type(error).__name__})
    finally:
        if record["before"] is not None:
            try:
                record["after"] = snapshot(settings)
                auth_after = sessions(settings)
                record["auth_after"] = auth_after
                record["auth_session_delta"] = auth_after["total"] - record["auth_before"]["total"]
                # Expiry fixture intentionally sets a past interval beyond normal lifetime.
                record["session_evidence_ok"] = bool(
                    auth_after["valid_lifetimes"] or spec.id == "H5"
                )
                record["session_evidence_ok"] &= bool(
                    auth_after.get("valid_active_lifetimes", True)
                )
                if spec.id == "H1" and issued:
                    with connect(settings) as conn:
                        proof = conn.execute(
                            """SELECT user_id, revoked_at IS NULL AS active,
                            extract(epoch FROM expires_at-created_at)::int AS ttl_seconds
                            FROM auth_sessions WHERE token_digest=%s""",
                            (token_digest(issued),),
                        ).fetchone()
                    record["new_session_proof"] = proof
                    record["session_evidence_ok"] &= proof == {
                        "user_id": spec.actor_id,
                        "active": True,
                        "ttl_seconds": 900,
                    }
                if spec.id == "H5":
                    record["session_evidence_ok"] &= auth_after["expired"] == 1
                if spec.id == "H6":
                    record["session_evidence_ok"] &= auth_after["revoked"] == 1
            except Exception as error:
                record["errors"].append({"stage": "after_evidence", "type": type(error).__name__})
        record["finished_at"] = now()
    return record


def provenance():
    commit = os.environ.get("BOLA_EVALUATION_SOURCE_COMMIT")
    dirty = os.environ.get("BOLA_EVALUATION_SOURCE_DIRTY")
    if not commit:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Exact source commit is required")
    return {
        "commit": commit,
        "worktree_dirty": dirty in {True, "true"},
        "source_sha256": source_hashes(),
    }


def run(output: Path):
    from bola_lab.evaluation.reports import regenerate

    output.mkdir(parents=True, exist_ok=False)
    inventory = read_frozen("inventory.json")
    specs = scenarios(inventory)
    for name in ("inventory.json", "fixture.json", "inventory.json.sha256", "fixture.json.sha256"):
        (output / name).write_bytes((PACKAGE / name).read_bytes())
    inventory_hash = digest(PACKAGE / "inventory.json")
    manifest = {
        "schema_version": 1,
        "milestone": "M3-A",
        "started_at": now(),
        "finished_at": None,
        "configuration": "hardened",
        "implementation": "endpoint-specific",
        "inventory_sha256": inventory_hash,
        "fixture_sha256": digest(PACKAGE / "fixture.json"),
        "http_transport": "HTTPX TCP loopback to harness-owned Uvicorn subprocess",
        "python": platform.python_version(),
        "dependencies": {
            n: importlib.metadata.version(n)
            for n in ("httpx", "psycopg", "fastapi", "pydantic", "uvicorn")
        },
        "known_present_seeded_defects": [],
        "planned_defect_classes": ["B01", "B02", "B03", "B04", "B05"],
        "errors": [],
        "source": None,
        "database": DATABASE,
    }
    observations = []
    try:
        manifest["source"] = provenance()
        settings = evaluation_settings(os.environ["BOLA_EVALUATION_DATABASE_URL"])
        with psycopg.connect(
            settings.database_url.get_secret_value(), autocommit=True, connect_timeout=5
        ) as lock:
            if not lock.execute("SELECT pg_try_advisory_lock(3123056)").fetchone()[0]:
                raise RuntimeError("Another evaluation owns this database")
            migrate(settings)
            with connect(settings) as conn:
                manifest["postgres_version"] = conn.execute("SHOW server_version").fetchone()[
                    "server_version"
                ]
            with (
                live_server(settings) as client,
                (output / "observations.jsonl").open("w") as stream,
            ):
                for spec in specs:
                    record = execute(spec, settings, client, inventory_hash)
                    observations.append(record)
                    stream.write(json.dumps(record, sort_keys=True) + "\n")
                    stream.flush()
    except Exception as error:
        manifest["errors"].append({"stage": "run_setup_or_execution", "type": type(error).__name__})
    seen = {r["scenario_id"] for r in observations}
    with (output / "observations.jsonl").open("a") as stream:
        for spec in specs:
            if spec.id not in seen:
                record = {
                    "scenario_id": spec.id,
                    "inventory_sha256": inventory_hash,
                    "actor_id": spec.actor_id,
                    "request": spec.request,
                    "started_at": now(),
                    "finished_at": now(),
                    "request_sent": False,
                    "before": None,
                    "after": None,
                    "response": None,
                    "errors": [{"stage": "not_run", "type": "RunUnavailable"}],
                }
                stream.write(json.dumps(record, sort_keys=True) + "\n")
    manifest["finished_at"] = now()
    manifest["observations_sha256"] = digest(output / "observations.jsonl")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return regenerate(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stream-archive", action="store_true")
    args = parser.parse_args()
    metrics = run(args.output)
    if args.stream_archive:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for path in sorted(args.output.iterdir()):
                archive.add(path, arcname=path.name)
        print(
            "BOLA_EVIDENCE_BEGIN\n"
            + base64.b64encode(buffer.getvalue()).decode()
            + "\nBOLA_EVIDENCE_END"
        )
    else:
        print(json.dumps(metrics, indent=2))
    raise SystemExit(0 if metrics["run_passed"] else 1)


if __name__ == "__main__":
    main()
