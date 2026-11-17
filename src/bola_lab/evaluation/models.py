"""Frozen, independent research contracts and safe evidence utilities."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
DEFECTS = {
    "B01": "Unauthorized task detail disclosure",
    "B02": "Unauthorized task list disclosure",
    "B03": "Unauthorized task updates",
    "B04": "Unauthorized task deletion",
    "B05": "Unauthorized task creation",
}


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    category: Literal["authentication", "authorization", "validation", "functional"]
    actor_id: int
    request: dict
    setup: list[str]
    expected: dict
    defect_classes: list[str]
    permitted_control: bool


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_frozen(name: str, directory: Path = PACKAGE) -> dict:
    path = directory / name
    if digest(path) != (directory / (name + ".sha256")).read_text().split()[0]:
        raise ValueError("Frozen research artifact checksum mismatch")
    return json.loads(path.read_text())


def scenarios(inventory: dict | None = None) -> list[Scenario]:
    inventory = inventory if inventory is not None else read_frozen("inventory.json")
    items = [Scenario.model_validate(row) for row in inventory["scenarios"]]
    if len({s.id for s in items}) != len(items):
        raise ValueError("Duplicate scenario IDs")
    for s in items:
        if set(s.defect_classes) - DEFECTS.keys():
            raise ValueError("Unknown defect class")
        if s.permitted_control != (
            s.category == "authorization" and s.expected["permission"] == "allow"
        ):
            raise ValueError("Invalid permitted-control label")
    return items


def canonical(value):
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def ordered(rows):
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))


def source_hashes(root: Path = ROOT) -> dict:
    paths = []
    for directory in ("src", "tests", "migrations", "laboratory"):
        paths.extend(
            p
            for p in (root / directory).rglob("*")
            if p.is_file() and p.suffix in {".py", ".sql", ".json", ".sha256"}
        )
    paths.extend(
        root / name for name in ("pyproject.toml", "requirements.lock", "requirements-dev.lock")
    )
    return {str(path.relative_to(root)): digest(path) for path in sorted(paths)}


def sanitize(value, secrets=()):
    """Remove credentials, hashes and known issued tokens, including nested values."""
    sensitive = {
        "password",
        "password_hash",
        "access_token",
        "refresh_token",
        "token_digest",
        "authorization",
        "cookie",
        "set-cookie",
        "secret",
    }
    if isinstance(value, dict):
        return {
            key: "<redacted>" if key.lower() in sensitive else sanitize(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "<redacted>")
        if value.startswith("$argon2"):
            return "<redacted>"
    return value
