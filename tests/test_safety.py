import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from bola_lab.config import Settings
from bola_lab.seed import seed

URL = "postgresql://synthetic:password@127.0.0.1/bola_lab_test"
ROOT = Path(__file__).resolve().parents[1]


def test_safe_default():
    settings = Settings(database_url=URL)
    assert settings.authorization_mode == "hardened"
    assert settings.environment == "production"
    assert settings.bind_host == settings.publish_host == "127.0.0.1"
    assert settings.lab_opt_in is False
    assert settings.token_ttl_seconds == 900


@pytest.mark.parametrize("mode", ["baseline", "endpoint"])
@pytest.mark.parametrize(
    "environment,opt_in", [("production", False), ("production", True), ("lab", False)]
)
def test_unsafe_configuration_requires_lab_and_opt_in(mode, environment, opt_in):
    with pytest.raises(ValidationError, match="explicit lab_opt_in"):
        Settings(
            database_url=URL, authorization_mode=mode, environment=environment, lab_opt_in=opt_in
        )


@pytest.mark.parametrize("mode", ["baseline", "endpoint"])
def test_m1_rejects_even_opted_in_experiments(mode):
    with pytest.raises(ValidationError, match="not implemented in M1"):
        Settings(database_url=URL, authorization_mode=mode, environment="lab", lab_opt_in=True)


def test_unsafe_wildcard_bind_rejected():
    with pytest.raises(ValidationError, match="loopback bind"):
        Settings(
            database_url=URL,
            authorization_mode="baseline",
            environment="lab",
            lab_opt_in=True,
            bind_host="0.0.0.0",
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"authorization_mode": "typo"},
        {"publish_host": "0.0.0.0"},
        {"publish_host": "example.com"},
        {"token_ttl_seconds": 901},
        {"token_ttl_seconds": 0},
        {"port": 80},
        {"environment": "typo"},
        {"database_url": "sqlite:///local.db"},
        {"database_url": "dbname=missing-host"},
    ],
)
def test_invalid_settings_rejected(changes):
    with pytest.raises(ValidationError):
        Settings(**({"database_url": URL} | changes))


def test_seed_requires_explicit_lab_opt_in():
    for environment, opt_in in (("production", True), ("lab", False), ("test", True)):
        with pytest.raises(ValueError, match="explicit lab_opt_in"):
            seed(Settings(database_url=URL, environment=environment, lab_opt_in=opt_in))


def test_cli_rejects_unsafe_startup_before_connecting():
    process = subprocess.run(
        [sys.executable, "-m", "bola_lab.cli", "serve"],
        env={
            **os.environ,
            "BOLA_DATABASE_URL": URL,
            "BOLA_AUTHORIZATION_MODE": "baseline",
            "BOLA_ENVIRONMENT": "production",
            "BOLA_LAB_OPT_IN": "false",
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert process.returncode != 0
    assert "explicit lab_opt_in" in process.stderr
    assert URL not in process.stderr
    assert "OperationalError" not in process.stderr


def test_compose_is_local_only_and_cannot_select_a_publish_address():
    configuration = yaml.safe_load((ROOT / "compose.yaml").read_text())
    services = configuration["services"]
    assert services["api"]["ports"] == ["127.0.0.1:8000:8000"]
    assert "ports" not in services["db"]
    assert services["db"].get("network_mode") != "host"
    assert configuration["networks"]["lab"]["internal"] is True
    for name, service in services.items():
        assert service.get("network_mode") != "host"
        assert service["networks"] == ["lab"]
        if name != "api":
            assert "ports" not in service
    assert services["api"]["environment"]["BOLA_AUTHORIZATION_MODE"].endswith(":-hardened}")
    assert services["api"]["read_only"] is True


def test_ci_has_no_deploy_step():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    assert set(workflow["jobs"]) == {"test"}
    assert workflow["permissions"] == {"contents": "read"}
    assert not any("deploy" in str(step).lower() for step in workflow["jobs"]["test"]["steps"])
