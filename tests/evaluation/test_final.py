"""Independent final-methodology and actual database authorization regression tests."""

import json
import socket
from copy import deepcopy

import pytest
from fastapi import HTTPException

from bola_lab.evaluation import detector, truth
from bola_lab.evaluation.checks import sort_state
from bola_lab.evaluation.models import read_frozen, scenarios
from bola_lab.policy import ProjectScope, authorize

SPECS = {s.id: s for s in scenarios()}
STATE = sort_state(read_frozen("fixture.json")["state"])


def observation(id):
    spec = SPECS[id]
    return {
        "scenario_id": id,
        "before": deepcopy(STATE),
        "after": deepcopy(STATE),
        "request_sent": True,
        "started_at": "2026-11-16T00:00:00+00:00",
        "finished_at": "2026-11-16T00:00:01+00:00",
        "response": {
            "status": spec.expected["status"],
            "body": deepcopy(spec.expected["response"]),
            "headers": {"cache-control": "no-store"},
        },
        "errors": [],
        "auth_session_delta": 0,
        "session_evidence_ok": True,
    }


def test_fabricated_nonexistent_record_is_not_confirmed_disclosure():
    row = observation("N2")
    row["response"]["body"] = {"id": 999999, "title": "Invented nonexistent synthetic record"}
    assert truth.disclosures(SPECS["N2"], row) == []
    assert truth.evaluate(SPECS["N2"], row)["enforcement"] == "compliant"
    assert not truth.contract(SPECS["N2"], row)
    assert detector.detect(SPECS["N2"], row)["verdict"] == "no_finding"


def test_title_only_actual_protected_content_is_independently_confirmed():
    row = observation("N2")
    row["response"]["body"] = {"title": "Synthetic task 1"}
    assert truth.disclosures(SPECS["N2"], row) == [
        {"table": "tasks", "id": 1, "matched_field": "title"}
    ]
    # The narrower detector may miss this; ground truth must not follow detector output.
    assert detector.detect(SPECS["N2"], row)["verdict"] == "no_finding"


@pytest.mark.parametrize("status", [200, 403, 500])
def test_actual_forbidden_mutation_is_confirmed_even_on_error(status):
    row = observation("N4")
    row["response"]["status"] = status
    row["after"]["tasks"][0]["title"] = "Forbidden"
    if status == 500:
        row["errors"] = [{"stage": "response", "type": "HTTP5xx"}]
    assert truth.evaluate(SPECS["N4"], row)["enforcement"] == "unauthorized_success"
    assert detector.detect(SPECS["N4"], row)["classes"] == ["B03"]


def test_wrong_but_permitted_field_change_is_functional_not_bola():
    row = observation("E2")
    row["after"]["tasks"][0]["description"] = "Unrequested but writable field"
    assert truth.mutations(SPECS["E2"], row) == []
    assert not truth.contract(SPECS["E2"], row)


def test_allowed_list_leak_is_not_a_false_positive():
    row = observation("L3")
    row["response"]["body"] = deepcopy(STATE["tasks"])
    assert truth.evaluate(SPECS["L3"], row)["enforcement"] == "unauthorized_success"
    assert detector.detect(SPECS["L3"], row)["classes"] == ["B02"]


def test_supplement_and_control_registry_do_not_change_frozen_core():
    core = read_frozen("inventory.json")
    supplement = scenarios(read_frozen("supplement.json"))
    assert core["inventory_version"] == "m3a-2" and len(core["scenarios"]) == 56
    assert len(supplement) == 6 and {s.id for s in supplement} == {f"S{i}" for i in range(1, 7)}
    controls = read_frozen("registry.json")["negative_controls"]
    assert "L3" not in controls and "L6" not in controls
    assert all(SPECS[id].permitted_control for id in controls)


@pytest.mark.parametrize(
    "role,action",
    [
        ("unknown", "tasks.read"),
        ("owner", "unknown"),
        ("viewer", "tasks.update"),
        ("editor", "tasks.delete"),
    ],
)
def test_central_policy_denies_by_default(role, action):
    with pytest.raises(HTTPException) as error:
        authorize(ProjectScope(1, 1, 1, role), action)
    assert error.value.status_code == 403


def test_baseline_requires_explicit_opt_in(monkeypatch):
    from laboratory.app import create_lab_app

    monkeypatch.delenv("BOLA_LOCAL_DEFECT_LAB", raising=False)
    with pytest.raises(ValueError, match="opt-in"):
        create_lab_app()


@pytest.mark.parametrize("environment,host", [("production", "127.0.0.1"), ("lab", "0.0.0.0")])
def test_baseline_rejects_unsafe_environment(monkeypatch, environment, host):
    from laboratory.app import create_lab_app

    monkeypatch.setenv("BOLA_LOCAL_DEFECT_LAB", "explicit-synthetic-lab-only")
    monkeypatch.setenv("BOLA_ENVIRONMENT", environment)
    monkeypatch.setenv("BOLA_BIND_HOST", host)
    with pytest.raises(ValueError, match="loopback"):
        create_lab_app()


def test_baseline_checks_actual_listener_not_just_environment(monkeypatch):
    from laboratory.app import create_lab_app

    monkeypatch.setenv("BOLA_LOCAL_DEFECT_LAB", "explicit-synthetic-lab-only")
    monkeypatch.setenv("BOLA_ENVIRONMENT", "lab")
    monkeypatch.setenv("BOLA_BIND_HOST", "127.0.0.1")
    monkeypatch.setenv(
        "BOLA_DATABASE_URL", "postgresql://synthetic@127.0.0.1/bola_lab_evaluation_test"
    )
    with socket.socket() as listener:
        listener.bind(("0.0.0.0", 0))
        listener.listen()
        monkeypatch.setenv("BOLA_LAB_LISTENER_FD", str(listener.fileno()))
        with pytest.raises(ValueError, match="not loopback"):
            create_lab_app()


@pytest.mark.integration
def test_scoped_sql_checks_actual_membership_and_role(seeded_database):
    from bola_lab import scoped_repository as data
    from bola_lab.db import connect
    from bola_lab.resources import ProjectPatch, TaskPatch

    with connect(seeded_database) as conn:
        with pytest.raises(HTTPException):
            data.task(conn, ProjectScope(1, 1, 4, "owner"), 1)
        assert (
            data.update_task(conn, ProjectScope(1, 1, 4, "owner"), 1, TaskPatch(title="Forbidden"))
            is None
        )
        with pytest.raises(HTTPException):
            data.update_project(
                conn, ProjectScope(1, 1, 3, "owner"), ProjectPatch(name="Forbidden")
            )
        assert (
            conn.execute("SELECT name FROM projects WHERE id=1").fetchone()["name"]
            == "Alpha Collaboration"
        )


def test_invalid_study_setup_is_preserved_not_counted_as_success(tmp_path, monkeypatch):
    from bola_lab.evaluation.study import run

    monkeypatch.setenv("BOLA_EVALUATION_SOURCE_COMMIT", "a" * 40)
    monkeypatch.setenv(
        "BOLA_EVALUATION_DATABASE_URL", "postgresql://synthetic@127.0.0.1/wrong_database"
    )
    out = tmp_path / "failed"
    result = run(out)
    assert not result["run_passed"]
    assert result["treatments"]["baseline"]["core"]["enforcement_accuracy"]["value"] is None
    assert len((out / "baseline/observations.jsonl").read_text().splitlines()) == 62
    assert json.loads((out / "manifest.json").read_text())["errors"]["run"]
