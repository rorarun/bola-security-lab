import json

import pytest

from bola_lab.evaluation.models import digest
from bola_lab.evaluation.reports import regenerate
from bola_lab.evaluation.runner import run


def incomplete_run(tmp_path, monkeypatch):
    # Invalid local-only settings fail before any connection, not a remote network experiment.
    monkeypatch.setenv("BOLA_EVALUATION_SOURCE_COMMIT", "a" * 40)
    monkeypatch.setenv(
        "BOLA_EVALUATION_DATABASE_URL", "postgresql://synthetic@127.0.0.1/wrong_database"
    )
    directory = tmp_path / "failed-run"
    metrics = run(directory)
    return directory, metrics


def test_whole_run_setup_failure_is_preserved_without_invented_executions(tmp_path, monkeypatch):
    directory, metrics = incomplete_run(tmp_path, monkeypatch)
    assert metrics["counts"]["planned"] == 56
    assert metrics["counts"]["request_attempted"] == 0
    assert metrics["counts"]["http_responses_received"] == 0
    assert metrics["counts"]["passed"] == 0
    assert metrics["counts"]["inconclusive"] == 56
    assert not metrics["run_passed"] and not metrics["run_complete"]
    assert metrics["authorization_enforcement_accuracy"]["value"] is None
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["errors"] == [{"stage": "run_setup_or_execution", "type": "ValueError"}]


def test_derived_reports_regenerate_byte_for_byte(tmp_path, monkeypatch):
    directory, _ = incomplete_run(tmp_path, monkeypatch)
    names = ("metrics.json", "evaluations.json", "observations.csv", "junit.xml", "summary.md")
    original = {name: digest(directory / name) for name in names}
    regenerate(directory)
    assert {name: digest(directory / name) for name in names} == original


def test_report_rejects_modified_observations(tmp_path, monkeypatch):
    directory, _ = incomplete_run(tmp_path, monkeypatch)
    path = directory / "observations.jsonl"
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="checksum"):
        regenerate(directory)
