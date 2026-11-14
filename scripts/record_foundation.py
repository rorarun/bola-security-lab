"""Record actual foundation verification, never synthetic BOLA metrics."""

import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path


def output(*arguments):
    return subprocess.check_output(arguments, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("junit", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    cases = list(ET.parse(args.junit).getroot().iter("testcase"))
    totals = {
        "tests": len(cases),
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skipped": sum(case.find("skipped") is not None for case in cases),
    }
    totals["passed"] = totals["tests"] - sum(
        totals[key] for key in ("failures", "errors", "skipped")
    )
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    hashes = {}
    for name in sorted(set(names.decode().split("\0"))):
        path = Path(name)
        if path.is_file() and not name.startswith("results/"):
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    compose = json.loads(output("docker", "compose", "config", "--format", "json"))
    api_binding = json.loads(
        output(
            "docker",
            "inspect",
            "bola-security-lab-api-1",
            "--format",
            "{{json .HostConfig.PortBindings}}",
        )
    )
    db_binding = json.loads(
        output(
            "docker",
            "inspect",
            "bola-security-lab-db-1",
            "--format",
            "{{json .HostConfig.PortBindings}}",
        )
    )
    # Check the actual tested image, so an unrebuilt image cannot silently attest newer source.
    image_probe = """
import hashlib, importlib.metadata, json, platform
from pathlib import Path
paths = [Path(name) for name in (
    'pyproject.toml', 'requirements.lock', 'requirements-dev.lock',
    'compose.yaml', '.github/workflows/ci.yml')]
for directory, pattern in (('src', '*.py'), ('tests', '*.py'), ('migrations', '*.sql')):
    paths.extend(Path(directory).rglob(pattern))
print(json.dumps({
    'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    'python': platform.python_version(),
    'packages': {name: importlib.metadata.version(name) for name in
                 ('fastapi', 'pydantic', 'psycopg', 'argon2-cffi', 'pytest', 'httpx')},
}))
"""
    tested = json.loads(
        output(
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "python",
            "bola-security-lab-test",
            "-c",
            image_probe,
        )
    )
    tested_names = {
        "pyproject.toml",
        "requirements.lock",
        "requirements-dev.lock",
        "compose.yaml",
        ".github/workflows/ci.yml",
    }
    expected_tested = {
        name: digest
        for name, digest in hashes.items()
        if name in tested_names
        or (name.startswith(("src/", "tests/")) and name.endswith(".py"))
        or (name.startswith("migrations/") and name.endswith(".sql"))
    }
    if expected_tested != tested["files"]:
        raise SystemExit("Test image source differs from checkout; rebuild and rerun verification")
    manifest = {
        "evidence_kind": "M1 foundation verification, not a BOLA experiment",
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "base_commit": output("git", "rev-parse", "HEAD"),
        "git_status": output("git", "status", "--porcelain"),
        "source_sha256": hashes,
        "tested_image_source_matches_checkout": True,
        "tested_image": tested,
        "junit_sha256": hashlib.sha256(args.junit.read_bytes()).hexdigest(),
        "test_counts": totals,
        "verification_complete": bool(cases)
        and not any(totals[key] for key in ("failures", "errors", "skipped")),
        "images": {
            image: output("docker", "image", "inspect", image, "--format", "{{.Id}}")
            for image in (
                "bola-security-lab-api",
                "bola-security-lab-test",
                "postgres:17.7-bookworm",
            )
        },
        "postgres_version": output(
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "bola_lab",
            "-d",
            "bola_lab_test",
            "-Atc",
            "SHOW server_version",
        ),
        "api_port_bindings": api_binding,
        "database_port_bindings": db_binding,
        "configured_authorization_mode": compose["services"]["api"]["environment"][
            "BOLA_AUTHORIZATION_MODE"
        ],
        "experiment_metrics": None,
        "limitations": [
            "Hosted GitHub Actions has not executed this uncommitted work.",
            "Normal Docker build failed cloud-proxy certificate validation; "
            "verified via temporary CA-secret adaptation.",
            "Host-shell published-port curl failed; live HTTP demo verified inside API container.",
            "Starlette reports HTTPX TestClient deprecation; HTTPX requirement retained.",
            "Resource authorization, seeded flaws, experimental metrics "
            "and concurrency testing deferred.",
        ],
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(totals))


if __name__ == "__main__":
    main()
