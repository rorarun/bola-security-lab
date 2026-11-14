"""Real local HTTP collaboration demo; emit requests/responses without credentials or tokens."""

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000"
EVENTS = []


def call(method, path, *, token=None, body=None, expected=200, record=True):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        BASE + path,
        method=method,
        headers=headers,
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        content = response.read()
        payload = json.loads(content) if content else None
        status = response.code
    if record:
        EVENTS.append(
            {
                "method": method,
                "path": path,
                "request_body": body,
                "status": status,
                "response": payload,
            }
        )
    assert status == expected, f"Unexpected status for {method} {path}: {status}"
    return payload


def main():
    tokens = {}
    for actor in (
        "owner@alpha.example",
        "editor@alpha.example",
        "viewer@alpha.example",
        "outsider@alpha.example",
        "owner@beta.example",
    ):
        issued = call(
            "POST",
            "/auth/token",
            record=False,
            body={
                "email": actor,
                "password": "Synthetic-Lab-Only-2026!",
            },
        )
        tokens[actor] = issued["access_token"]
    owner, editor, viewer, outsider, cross_org = tokens.values()
    project = call(
        "POST",
        "/organizations/1/projects",
        token=owner,
        expected=201,
        body={"name": "Verified M2 collaboration", "description": "Synthetic demo only"},
    )
    path = f"/organizations/1/projects/{project['id']}"
    try:
        for user_id, role in ((2, "editor"), (3, "viewer")):
            call(
                "POST",
                path + "/memberships",
                token=owner,
                expected=201,
                body={"user_id": user_id, "role": role},
            )
        task = call(
            "POST",
            path + "/tasks",
            token=editor,
            expected=201,
            body={"title": "Collaborative synthetic task"},
        )
        task_path = path + f"/tasks/{task['id']}"
        edited = call("PATCH", task_path, token=editor, body={"status": "done"})
        assert edited["created_by"] == 2 and edited["status"] == "done"
        visible = call("GET", task_path, token=viewer)
        assert visible["status"] == "done" and visible["id"] == task["id"]
        call("PATCH", task_path, token=viewer, body={"title": "Forbidden"}, expected=403)
        call("DELETE", task_path, token=editor, expected=403)
        for token in (outsider, cross_org):
            call("GET", task_path, token=token, expected=404)
        # Prove task 1 exists under its real parent before using a mismatched project path.
        original = call("GET", "/organizations/1/projects/1/tasks/1", token=owner)
        assert original["project_id"] == 1
        call("GET", path + "/tasks/1", token=owner, expected=404)
        listing = call("GET", path + "/tasks", token=viewer)
        assert [row["id"] for row in listing] == [task["id"]]
        call("DELETE", path + "/memberships/3", token=owner, expected=204)
        call("GET", task_path, token=viewer, expected=404)
        call("GET", "/users/me", token=viewer)  # session remains valid after project revocation
        call("DELETE", task_path, token=owner, expected=204)
        assert call("GET", path + "/tasks", token=owner) == []
    finally:
        call("DELETE", path, token=owner, expected=204)
        for token in tokens.values():
            call("DELETE", "/auth/token", token=token, expected=204, record=False)
    call("GET", path, token=owner, expected=401, record=False)
    print(
        json.dumps(
            {"implementation": "endpoint-specific", "result": "passed", "events": EVENTS}, indent=2
        )
    )


if __name__ == "__main__":
    main()
