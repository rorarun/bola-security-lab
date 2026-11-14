"""Run through stdin inside the API container; never print bearer tokens."""

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000"


def request(method, path, *, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urlopen(
            Request(BASE + path, data=data, headers=headers, method=method), timeout=5
        ) as response:
            content = response.read()
            return response.status, json.loads(content) if content else None
    except HTTPError as error:
        return error.code, json.loads(error.read())


def main():
    status, readiness = request("GET", "/health/ready")
    assert status == 200 and readiness == {"status": "ready"}
    status, issued = request(
        "POST",
        "/auth/token",
        body={
            "email": "owner@alpha.example",
            "password": "Synthetic-Lab-Only-2026!",
        },
    )
    assert status == 200 and issued["expires_in"] == 900
    token = issued["access_token"]
    status, user = request("GET", "/users/me", token=token)
    assert status == 200 and user == {"id": 1, "email": "owner@alpha.example"}
    assert request("DELETE", "/auth/token", token=token)[0] == 204
    assert request("GET", "/users/me", token=token)[0] == 401
    print(
        json.dumps(
            {
                "ready": readiness,
                "identity": user,
                "logout_status": 204,
                "revoked_token_status": 401,
                "result": "passed",
            }
        )
    )


if __name__ == "__main__":
    main()
