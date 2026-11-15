import json
from copy import deepcopy

import pytest

from bola_lab.evaluation.checks import detect, evaluate, sort_state
from bola_lab.evaluation.models import PACKAGE, read_frozen, sanitize, scenarios
from bola_lab.evaluation.reports import summarize
from bola_lab.evaluation.runner import evaluation_settings

SPECS = {s.id: s for s in scenarios()}
FIXTURE = sort_state(read_frozen("fixture.json")["state"])
START = "2026-11-15T00:00:00+00:00"
END = "2026-11-15T00:00:01+00:00"


def denied_observation(id="N4"):
    spec = SPECS[id]
    return {
        "scenario_id": id,
        "before": deepcopy(FIXTURE),
        "after": deepcopy(FIXTURE),
        "response": {
            "status": spec.expected["status"],
            "body": spec.expected["response"],
            "headers": {"cache-control": "no-store"},
        },
        "started_at": START,
        "finished_at": END,
        "request_sent": True,
        "errors": [],
        "auth_session_delta": 0,
        "session_evidence_ok": True,
    }


def allowed_read():
    row = denied_observation("C1")
    row["response"]["body"] = deepcopy(next(r for r in FIXTURE["tasks"] if r["id"] == 1))
    return row


def test_frozen_inventory_has_stable_ids_and_computed_eligibility():
    items = scenarios()
    expected_ids = {f"{group}{i}" for group in "HCANXLIR" for i in range(1, 7)}
    expected_ids |= {f"E{i}" for i in range(1, 9)}
    assert {s.id for s in items} == expected_ids
    assert len(items) == 56
    eligible = [s for s in items if s.category == "authorization"]
    assert len(eligible) == 47
    assert sum(s.expected["permission"] == "allow" for s in eligible) == 18
    assert sum(s.expected["permission"] == "deny" for s in eligible) == 29
    assert {d for s in items for d in s.defect_classes} == {f"B0{i}" for i in range(1, 6)}
    assert not SPECS["H1"].defect_classes and not SPECS["A6"].defect_classes


def test_checksum_rejects_changed_expected_outcome(tmp_path):
    for name in ("inventory.json", "inventory.json.sha256"):
        (tmp_path / name).write_bytes((PACKAGE / name).read_bytes())
    data = json.loads((tmp_path / "inventory.json").read_text())
    data["scenarios"][0]["expected"]["status"] = 403
    (tmp_path / "inventory.json").write_text(json.dumps(data))
    with pytest.raises(ValueError, match="checksum"):
        read_frozen("inventory.json", tmp_path)


def test_membership_control_uses_documented_user_id_order():
    # Regression for the explicitly preserved v1 oracle ordering mistake.
    assert [r["user_id"] for r in SPECS["E5"].expected["response"]] == [1, 2, 3]


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://synthetic@127.0.0.1/bola_lab",
        "postgresql://synthetic@127.0.0.1/bola_lab_test",
        "postgresql://synthetic@example.com/bola_lab_evaluation_test",
        "postgresql://synthetic@127.0.0.1/bola_lab_evaluation_test?hostaddr=203.0.113.9",
    ],
)
def test_evaluation_rejects_wrong_database_or_remote_connection(url):
    with pytest.raises(ValueError):
        evaluation_settings(url)


def test_evaluation_settings_are_defensive_and_local():
    settings = evaluation_settings("postgresql://synthetic@127.0.0.1/bola_lab_evaluation_test")
    assert settings.authorization_mode == "hardened"
    assert settings.bind_host == "127.0.0.1" and not settings.lab_opt_in


@pytest.mark.parametrize("status", [200, 403, 500])
def test_forbidden_database_update_is_violation_even_with_denial_or_server_error(status):
    observation = denied_observation()
    observation["response"]["status"] = status
    observation["after"]["tasks"][0]["title"] = "Synthetic unauthorized change"
    if status == 500:
        observation["errors"] = [{"stage": "application_response", "type": "HTTP5xx"}]
    result = evaluate(SPECS["N4"], observation)
    assert result["enforcement"] == "unauthorized_success"
    assert result["status"] == "failed" and not result["database_contract_pass"]
    assert result["detector"]["classes"] == ["B03"]
    summary = summarize([SPECS["N4"]], [observation], [result])
    assert summary["unauthorized_operation_success_rate"]["value"] == 1
    assert summary["authorization_enforcement_accuracy"]["value"] == 0


@pytest.mark.parametrize(
    "stage",
    [
        "fixture",
        "authentication_setup",
        "scenario_setup",
        "http_request",
        "after_evidence",
        "not_run",
    ],
)
def test_execution_failures_never_become_successful_enforcement(stage):
    observation = denied_observation()
    observation["response"] = None
    observation["after"] = None
    observation["request_sent"] = stage in {"http_request", "after_evidence"}
    observation["errors"] = [{"stage": stage, "type": "SyntheticFailure"}]
    result = evaluate(SPECS["N4"], observation)
    summary = summarize([SPECS["N4"]], [observation], [result])
    assert result["enforcement"] == "inconclusive" and result["status"] == "inconclusive"
    assert summary["authorization_enforcement_accuracy"]["denominator"] == 0
    assert summary["authorization_enforcement_accuracy"]["value"] is None
    assert summary["unauthorized_operation_success_rate"]["value"] is None
    assert not summary["run_complete"] and not summary["run_passed"]


def test_denied_response_with_missing_database_evidence_is_inconclusive():
    observation = denied_observation()
    observation["after"] = None
    observation["errors"] = [{"stage": "after_evidence", "type": "OperationalError"}]
    assert evaluate(SPECS["N4"], observation)["status"] == "inconclusive"


@pytest.mark.parametrize(
    "id,defect", [("N2", "B01"), ("L4", "B02"), ("N4", "B03"), ("N5", "B04"), ("N3", "B05")]
)
def test_detector_on_independently_labelled_violating_observation_fixtures(id, defect):
    # These are calibration data only, never an insecure API implementation or live result.
    observation = denied_observation(id)
    task = deepcopy(next(r for r in FIXTURE["tasks"] if r["id"] == 1))
    if defect == "B01":
        observation["response"]["body"] = task
    elif defect == "B02":
        observation["response"]["body"] = [task]
    elif defect == "B03":
        observation["after"]["tasks"][0]["title"] = "Changed"
    elif defect == "B04":
        observation["after"]["tasks"] = [r for r in observation["after"]["tasks"] if r["id"] != 1]
    else:
        observation["after"]["tasks"].append(task | {"id": 4})
    finding = detect(SPECS[id], observation)
    assert finding["verdict"] == "finding" and finding["classes"] == [defect]


def test_repeated_findings_are_one_distinct_class_and_not_live_seeded_recall():
    observations = [denied_observation(id) for id in ("N4", "X5")]
    for row in observations:
        row["after"]["tasks"][0]["title"] = "Changed"
    specs = [SPECS["N4"], SPECS["X5"]]
    results = [evaluate(s, r) for s, r in zip(specs, observations, strict=True)]
    summary = summarize(specs, observations, results)
    assert summary["detector_findings"]["observation_count"] == 2
    assert summary["detector_findings"]["distinct_observed_class_count"] == 1
    assert summary["live_seeded_defect_recall"]["value"] is None
    assert summary["live_seeded_defect_recall"]["denominator"] == 0


def test_false_positive_rate_uses_independent_compliant_control_labels():
    observation = allowed_read()
    result = evaluate(SPECS["C1"], observation)
    assert result["functional_pass"] and result["enforcement"] == "compliant"
    # Independently label a hypothetical detector output as a false alarm for arithmetic testing.
    result["detector"] = {
        "verdict": "finding",
        "classes": [],
        "evidence": ["calibration_false_alarm"],
    }
    summary = summarize([SPECS["C1"]], [observation], [result])
    assert summary["detector_false_positive_rate"]["numerator"] == 1
    assert summary["detector_false_positive_rate"]["denominator"] == 1
    assert summary["detector_false_positive_rate"]["value"] == 1


def test_incorrect_denial_is_legitimate_failure_not_a_detector_false_positive():
    observation = allowed_read()
    observation["response"] = {
        "status": 403,
        "body": {"detail": "Insufficient project role"},
        "headers": {"cache-control": "no-store"},
    }
    result = evaluate(SPECS["C1"], observation)
    summary = summarize([SPECS["C1"]], [observation], [result])
    assert result["enforcement"] == "incorrect_denial"
    assert result["detector"]["verdict"] == "no_finding"
    assert summary["legitimate_operation_success_rate"]["value"] == 0
    assert summary["detector_false_positive_rate"]["numerator"] == 0
    assert summary["detector_false_positive_rate"]["value"] is None
    assert summary["detector_false_positive_rate"]["excluded_ids"] == ["C1"]


def test_wrong_task_content_is_functional_failure_without_bola_finding():
    observation = allowed_read()
    observation["response"]["body"]["title"] = "Wrong synthetic title"
    result = evaluate(SPECS["C1"], observation)
    assert result["enforcement"] == "compliant"
    assert not result["functional_pass"] and result["status"] == "failed"
    assert result["detector"]["verdict"] == "no_finding"


def test_secret_redaction_is_recursive_and_removes_embedded_known_values():
    value = {
        "outer": [
            {"Authorization": "Bearer synthetic-token", "password_hash": "$argon2id$example"}
        ],
        "message": "embedded-token-secret",
        "access_token": "opaque-secret",
    }
    serialized = json.dumps(sanitize(value, ["token-secret"]))
    assert "synthetic-token" not in serialized and "argon2id" not in serialized
    assert "opaque-secret" not in serialized and "token-secret" not in serialized
