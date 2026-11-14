"""Ordered SQL migrations with checksums, a transaction, and a cross-process lock."""

import hashlib
from pathlib import Path

from bola_lab.config import Settings
from bola_lab.db import connect

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def migration_files(directory: Path = MIGRATIONS) -> list[tuple[str, str, str]]:
    files = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    if not files:
        raise RuntimeError("No migration files found")
    return [
        (path.name, hashlib.sha256(path.read_bytes()).hexdigest(), path.read_text())
        for path in files
    ]


def migrate(settings: Settings, directory: Path = MIGRATIONS) -> None:
    files = migration_files(directory)
    with connect(settings) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(3123001)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name text PRIMARY KEY,
                sha256 text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
        """)
        applied = {
            row["name"]: row["sha256"] for row in conn.execute("SELECT * FROM schema_migrations")
        }
        expected = {name: digest for name, digest, _ in files}
        if any(expected.get(name) != digest for name, digest in applied.items()):
            raise RuntimeError(
                "Applied migration missing or modified; do not rewrite migration history"
            )
        for name, digest, contents in files:
            if name not in applied:
                conn.execute(contents)
                conn.execute(
                    "INSERT INTO schema_migrations (name, sha256) VALUES (%s, %s)", (name, digest)
                )


def verify_schema(settings: Settings) -> None:
    expected = {name: digest for name, digest, _ in migration_files()}
    with connect(settings) as conn:
        actual = {
            row["name"]: row["sha256"] for row in conn.execute("SELECT * FROM schema_migrations")
        }
    if actual != expected:
        raise RuntimeError(
            "Database migrations do not match this application; run bola-lab migrate"
        )
