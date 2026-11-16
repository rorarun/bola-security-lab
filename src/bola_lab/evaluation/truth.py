"""Independent ground truth from actual entities and membership facts."""

from bola_lab.evaluation.checks import delta, expected_state, matches, sort_state


def _role(state, actor, org, project):
    if not any(
        r["organization_id"] == org and r["user_id"] == actor
        for r in state["organization_memberships"]
    ):
        return None
    return next(
        (
            r["role"]
            for r in state["project_memberships"]
            if r["project_id"] == project and r["organization_id"] == org and r["user_id"] == actor
        ),
        None,
    )


def disclosures(spec, observation):
    state = observation.get("before")
    if state is None:
        return []
    body = (observation.get("response") or {}).get("body")
    records = body if isinstance(body, list) else [body]
    path = spec.request["path"].split("/")
    org = int(path[2]) if len(path) > 2 and path[2].isdigit() else None
    project = int(path[4]) if len(path) > 4 and path[4].isdigit() else None
    findings = []
    for payload in records:
        if not isinstance(payload, dict):
            continue
        for table in ("tasks", "projects", "organizations"):
            field = "title" if table == "tasks" else "name"
            if not isinstance(payload.get(field), str) or not payload[field]:
                continue
            candidates = [
                r
                for r in state[table]
                if r[field] == payload[field] and ("id" not in payload or r["id"] == payload["id"])
            ]
            # Content must identify a real protected entity; fabricated shapes are not evidence.
            if len(candidates) != 1:
                continue
            row = candidates[0]
            if table == "organizations":
                permitted = any(
                    m["organization_id"] == row["id"] and m["user_id"] == spec.actor_id
                    for m in state["organization_memberships"]
                )
                permitted &= org is None or org == row["id"]
            else:
                entity_org = row["organization_id"]
                entity_project = row["project_id"] if table == "tasks" else row["id"]
                permitted = _role(state, spec.actor_id, entity_org, entity_project) in {
                    "owner",
                    "editor",
                    "viewer",
                }
                permitted &= org is None or org == entity_org
                permitted &= project is None or project == entity_project
            if not permitted:
                findings.append({"table": table, "id": row["id"], "matched_field": field})
    return findings


def mutations(spec, observation):
    before, after = observation.get("before"), observation.get("after")
    if before is None or after is None:
        return []
    path = spec.request["path"].split("/")
    org = int(path[2]) if len(path) > 2 and path[2].isdigit() else None
    project = int(path[4]) if len(path) > 4 and path[4].isdigit() else None
    changes = delta(before, after)
    findings = []
    for table, kinds in changes.items():
        for kind, rows in kinds.items():
            for change in rows:
                row = change["before"] if kind == "changed" else change
                permitted = False
                if table == "tasks":
                    role = _role(before, spec.actor_id, row["organization_id"], row["project_id"])
                    permitted = role in ({"owner"} if kind == "removed" else {"owner", "editor"})
                    permitted &= org == row["organization_id"] and project == row["project_id"]
                    if kind == "added":
                        permitted &= row["created_by"] == spec.actor_id
                    if kind == "changed":
                        permitted &= all(
                            change["after"][k] == row[k]
                            for k in (
                                "id",
                                "organization_id",
                                "project_id",
                                "created_by",
                                "created_at",
                            )
                        )
                elif table == "projects":
                    if kind == "added":
                        permitted = row["created_by"] == spec.actor_id and any(
                            m["organization_id"] == row["organization_id"]
                            and m["user_id"] == spec.actor_id
                            for m in before["organization_memberships"]
                        )
                    else:
                        permitted = (
                            _role(before, spec.actor_id, row["organization_id"], row["id"])
                            == "owner"
                            and project == row["id"]
                            and org == row["organization_id"]
                        )
                        if kind == "changed":
                            permitted &= all(
                                change["after"][k] == row[k]
                                for k in ("organization_id", "id", "created_by", "created_at")
                            )
                elif table == "project_memberships":
                    role = _role(before, spec.actor_id, row["organization_id"], row["project_id"])
                    newly_owned = any(
                        p["id"] == row["project_id"] and p["created_by"] == spec.actor_id
                        for p in changes["projects"]["added"]
                    )
                    deleted_parent = any(
                        p["id"] == row["project_id"] for p in changes["projects"]["removed"]
                    )
                    permitted = (
                        role == "owner"
                        and project == row["project_id"]
                        and org == row["organization_id"]
                    ) or newly_owned
                    if (
                        kind in {"changed", "removed"}
                        and row["role"] == "owner"
                        and not deleted_parent
                    ):
                        permitted = False
                elif table == "organizations" and kind == "added":
                    permitted = row["created_by"] == spec.actor_id
                elif table == "organization_memberships" and kind == "added":
                    permitted = row["user_id"] == spec.actor_id and any(
                        o["id"] == row["organization_id"] for o in changes["organizations"]["added"]
                    )
                if not permitted:
                    findings.append(
                        {
                            "table": table,
                            "operation": kind,
                            "id": row.get("id"),
                            "project_id": row.get("project_id"),
                        }
                    )
    return findings


def contract(spec, observation):
    if observation.get("errors") or any(
        observation.get(k) is None for k in ("response", "before", "after")
    ):
        return False
    response = observation["response"]
    start, end = observation["started_at"], observation["finished_at"]
    body_ok = matches(response["body"], spec.expected["response"], start, end)
    state_ok = matches(
        sort_state(observation["after"]),
        expected_state(observation["before"], spec.expected["effect"]),
        start,
        end,
    )
    return bool(
        response["status"] == spec.expected["status"]
        and body_ok
        and state_ok
        and observation.get("auth_session_delta") == spec.expected["auth_session_delta"]
        and observation.get("session_evidence_ok")
        and observation.get("auth_response_valid", True)
        and response["headers"].get("cache-control") == "no-store"
    )


def evaluate(spec, observation):
    leaks, writes = disclosures(spec, observation), mutations(spec, observation)
    complete = not observation.get("errors") and all(
        observation.get(k) is not None for k in ("before", "after", "response")
    )
    if leaks or writes:
        result = "unauthorized_success"
    elif not complete:
        result = "inconclusive"
    elif spec.category != "authorization":
        result = "not_applicable"
    elif spec.expected["permission"] == "allow":
        result = (
            "compliant" if 200 <= observation["response"]["status"] < 300 else "incorrect_denial"
        )
    else:
        result = (
            "compliant"
            if observation["response"]["status"] == spec.expected["status"]
            else "incorrect_decision"
        )
    passed = contract(spec, observation)
    status = (
        "passed"
        if passed and not leaks and not writes
        else "inconclusive"
        if result == "inconclusive"
        else "failed"
    )
    return {
        "scenario_id": spec.id,
        "status": status,
        "enforcement": result,
        "functional_pass": passed,
        "disclosures": leaks,
        "mutations": writes,
        "execution_errors": observation.get("errors", []),
    }
