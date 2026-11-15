from copy import deepcopy

import httpx
import pytest

from bola_lab.evaluation.models import scenarios
from bola_lab.evaluation.runner import evaluation_settings, execute


def test_transport_failure_is_recorded_and_post_state_still_collected(monkeypatch):
    from bola_lab.evaluation import runner

    base = {table: [] for table in runner.KEYS}
    monkeypatch.setattr(runner, "reset_fixture", lambda _: deepcopy(base))
    monkeypatch.setattr(runner, "login", lambda *_: "synthetic-memory-only")
    monkeypatch.setattr(runner, "prepare", lambda *args: [])
    monkeypatch.setattr(runner, "snapshot", lambda _: deepcopy(base))
    monkeypatch.setattr(runner, "sessions", lambda _: {"total": 7, "valid_lifetimes": True})

    class Offline:
        def request(self, *args, **kwargs):
            raise httpx.ConnectError("This diagnostic must never be persisted")

    record = execute(next(s for s in scenarios() if s.id == "N4"), None, Offline(), "frozen")
    assert record["response"] is None and record["after"] == base
    assert record["errors"] == [{"stage": "http_request", "type": "ConnectError"}]
    assert "diagnostic" not in str(record)


def test_failed_fixture_does_not_send_request(monkeypatch):
    from bola_lab.evaluation import runner

    def unavailable(_):
        raise RuntimeError("Synthetic setup failure")

    monkeypatch.setattr(runner, "reset_fixture", unavailable)
    record = execute(scenarios()[0], None, None, "frozen")
    assert not record["request_sent"] and record["before"] is None and record["after"] is None
    assert record["errors"] == [{"stage": "fixture", "type": "RuntimeError"}]


def test_live_server_really_rejects_failed_startup(monkeypatch):
    from bola_lab.evaluation import runner

    class Exited:
        def poll(self):
            return 1

        def terminate(self):
            pass

        def wait(self, **kwargs):
            pass

    monkeypatch.setattr(runner.subprocess, "Popen", lambda *args, **kwargs: Exited())
    settings = evaluation_settings("postgresql://synthetic@127.0.0.1/bola_lab_evaluation_test")
    with pytest.raises(RuntimeError, match="startup failed"), runner.live_server(settings):
        pytest.fail("Failed startup must not yield an HTTP client")
