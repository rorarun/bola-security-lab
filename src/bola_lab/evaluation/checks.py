"""Independent exact contract checks and permission-scope evaluation.

Only frozen research expectations and observations are used.
No application policy/repository imports.
"""

from copy import deepcopy
from datetime import datetime

from bola_lab.evaluation.models import ordered

KEYS = {
    "users": ("id",),
    "organizations": ("id",),
    "organization_memberships": ("organization_id", "user_id"),
    "projects": ("id",),
    "project_memberships": ("project_id", "user_id"),
    "tasks": ("id",),
}


def matches(actual, expected, started, finished):
    if expected == "@runtime":
        try:
            moment = datetime.fromisoformat(actual.replace("Z", "+00:00"))
            return datetime.fromisoformat(started) <= moment <= datetime.fromisoformat(finished)
        except (TypeError, ValueError, AttributeError):
            return False
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and actual.keys() == expected.keys()
            and all(matches(actual[k], v, started, finished) for k, v in expected.items())
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(matches(a, e, started, finished) for a, e in zip(actual, expected, strict=True))
        )
    return type(actual) is type(expected) and actual == expected


def expected_state(before, effect):
    result = deepcopy(before)
    kind = effect["kind"]
    if kind == "insert":
        result[effect["table"]].append(deepcopy(effect["row"]))
    elif kind in {"update", "delete"}:
        rows = result[effect["table"]]
        selected = [r for r in rows if all(r[k] == v for k, v in effect["key"].items())]
        if len(selected) != 1:
            raise ValueError("Expected target absent or ambiguous in pre-state")
        if kind == "update":
            selected[0].update(effect["values"])
        else:
            rows.remove(selected[0])
    elif kind == "project_create":
        row = deepcopy(effect["row"])
        result["projects"].append(row)
        result["project_memberships"].append(
            dict(
                organization_id=row["organization_id"],
                project_id=row["id"],
                user_id=row["created_by"],
                role="owner",
            )
        )
    elif kind == "project_delete":
        result["projects"] = [r for r in result["projects"] if r["id"] != effect["id"]]
        for table in ("tasks", "project_memberships"):
            result[table] = [r for r in result[table] if r["project_id"] != effect["id"]]
    elif kind != "none":
        raise ValueError("Unknown expected effect")
    # Sort by primary key: runtime placeholders must not influence row order.
    return {
        table: sorted(rows, key=lambda r: tuple(r[k] for k in KEYS[table]))
        for table, rows in result.items()
    }


def sort_state(state):
    return {
        table: sorted(rows, key=lambda r: tuple(r[k] for k in KEYS[table]))
        for table, rows in state.items()
    }


def delta(before, after):
    changes = {}
    for table, keys in KEYS.items():
        a = {tuple(r[k] for k in keys): r for r in before[table]}
        b = {tuple(r[k] for k in keys): r for r in after[table]}
        changes[table] = {
            "added": ordered([b[k] for k in b.keys() - a.keys()]),
            "removed": ordered([a[k] for k in a.keys() - b.keys()]),
            "changed": [
                {"before": a[k], "after": b[k]} for k in sorted(a.keys() & b.keys()) if a[k] != b[k]
            ],
        }
    return changes


def response_scope_violation(spec, body):
    """Missing/wrong content is functional; foreign resource identities are a scope violation."""
    if body is None:
        return False
    rows = body if isinstance(body, list) else [body]
    records = [
        r
        for r in rows
        if isinstance(r, dict)
        and "id" in r
        and any(k in r for k in ("title", "name", "project_id"))
    ]
    if spec.expected["permission"] == "deny":
        return bool(records)
    expected = spec.expected["response"]
    expected_rows = expected if isinstance(expected, list) else [expected]
    allowed = {r["id"]: r for r in expected_rows if isinstance(r, dict) and "id" in r}
    for row in records:
        if spec.request["method"] == "GET" and row["id"] not in allowed:
            return True
        reference = allowed.get(row["id"])
        if reference and any(
            row.get(k) != reference[k]
            for k in ("organization_id", "project_id", "created_by")
            if k in reference
        ):
            return True
    return False


def state_scope_violation(spec, before, after):
    changes = delta(before, after)
    effect = spec.expected["effect"]
    kind = effect["kind"]
    allowed = expected_state(before, effect)
    desired_changes = delta(before, allowed)
    for table, actual in changes.items():
        desired = desired_changes[table]
        # Extra affected objects or mutation kinds violate scope.
        # Missing effects are functional errors.
        for operation in ("added", "removed", "changed"):

            def key(row, operation=operation, table=table):
                r = row["after"] if operation == "changed" else row
                return tuple(r[k] for k in KEYS[table])

            expected_by_id = {key(r): r for r in desired[operation]}
            for row in actual[operation]:
                reference = expected_by_id.get(key(row))
                if reference is None:
                    return True
                current = row["after"] if operation == "changed" else row
                target = reference["after"] if operation == "changed" else reference
                if operation != "removed":
                    protected = ("organization_id", "project_id", "created_by", "user_id", "role")
                    if any(current.get(k) != target[k] for k in protected if k in target):
                        return True
                    if operation == "changed":
                        changed_fields = {k for k in current if current[k] != row["before"][k]}
                        permitted_fields = {
                            k for k in target if target[k] != reference["before"][k]
                        }
                        if changed_fields - permitted_fields:
                            return True
    return kind == "none" and before != after


def detect(spec, observation):
    """Task BOLA evidence classification, separate from HTTP/functional test success."""
    if spec.category != "authorization":
        return {"verdict": "not_applicable", "classes": [], "evidence": []}
    evidence, classes = [], set()
    before, after = observation.get("before"), observation.get("after")
    body = (observation.get("response") or {}).get("body")
    if response_scope_violation(spec, body):
        evidence.append("response_outside_permitted_scope")
        if spec.request["method"] == "GET":
            candidate = "B02" if spec.request["path"].endswith("/tasks") else "B01"
            if candidate in spec.defect_classes:
                classes.add(candidate)
    if before is not None and after is not None and spec.expected["permission"] == "deny":
        task_changes = delta(before, after)["tasks"]
        for operation, defect in (("added", "B05"), ("changed", "B03"), ("removed", "B04")):
            if task_changes[operation]:
                evidence.append("forbidden_task_" + operation)
                if defect in spec.defect_classes:
                    classes.add(defect)
    complete = before is not None and after is not None and observation.get("response") is not None
    return {
        "verdict": "finding" if evidence else ("no_finding" if complete else "inconclusive"),
        "classes": sorted(classes),
        "evidence": evidence,
    }


def evaluate(spec, observation):
    before, after = observation.get("before"), observation.get("after")
    response = observation.get("response")
    complete = before is not None and after is not None and response is not None
    errors = observation.get("errors", [])
    detector = detect(spec, observation)
    response_ok = state_ok = auth_ok = False
    scope_breach = response_scope_violation(spec, (response or {}).get("body"))
    if before is not None and after is not None:
        scope_breach |= state_scope_violation(spec, before, after)
    if complete:
        start, end = observation["started_at"], observation["finished_at"]
        response_ok = (
            response["status"] == spec.expected["status"]
            and matches(response["body"], spec.expected["response"], start, end)
            and response["headers"].get("cache-control") == "no-store"
        )
        state_ok = matches(
            sort_state(after), expected_state(before, spec.expected["effect"]), start, end
        )
        auth_ok = observation.get("auth_session_delta") == spec.expected["auth_session_delta"]
        # Public session facts, never raw tokens/digests, are mandatory evidence.
        auth_ok &= observation.get("session_evidence_ok", False)
        response_ok &= observation.get("auth_response_valid", True)
        # Matching response records must also agree with persisted records, including timestamps.
        if (
            response_ok
            and spec.category == "authorization"
            and spec.expected["permission"] == "allow"
        ):
            body = response["body"]
            rows = body if isinstance(body, list) else [body]
            resource = (
                "tasks"
                if "/tasks" in spec.request["path"]
                else "projects"
                if "/projects" in spec.request["path"]
                else "organizations"
            )
            if "/memberships" not in spec.request["path"]:
                response_ok &= all(
                    row in after[resource] for row in rows if isinstance(row, dict) and "id" in row
                )
    functional = complete and not errors and response_ok and state_ok and auth_ok
    if scope_breach:
        enforcement = "unauthorized_success"
    elif not complete or errors:
        enforcement = "inconclusive"
    elif spec.category != "authorization":
        enforcement = "not_applicable"
    elif spec.expected["permission"] == "allow":
        enforcement = "compliant" if 200 <= response["status"] < 300 else "incorrect_denial"
    else:
        enforcement = (
            "compliant" if response["status"] == spec.expected["status"] else "incorrect_decision"
        )
    status = (
        "passed"
        if functional and enforcement in {"compliant", "not_applicable"}
        else ("inconclusive" if enforcement == "inconclusive" else "failed")
    )
    return {
        "scenario_id": spec.id,
        "status": status,
        "enforcement": enforcement,
        "functional_pass": bool(functional),
        "response_contract_pass": bool(response_ok),
        "database_contract_pass": bool(state_ok),
        "session_contract_pass": bool(auth_ok),
        "detector": detector,
        "execution_errors": errors,
    }
