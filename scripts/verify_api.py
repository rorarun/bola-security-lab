"""Run M2 integration/regression checks; this is not the BOLA experiment runner."""

import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main():
    started = datetime.now(UTC).isoformat()
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--profile",
            "test",
            "run",
            "--rm",
            "test",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--junitxml=/dev/stdout",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    xml = re.search(r"<testsuites\b.*?</testsuites>", result.stdout, re.DOTALL)
    destination = Path("results/m2/junit.xml")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if xml:
        destination.write_text(xml.group() + "\n")
        print(result.stdout[: xml.start()] + result.stdout[xml.end() :])
        print(f"Preserved {destination}")
    else:
        print(result.stdout)
        print("JUnit was not produced; verification is incomplete.", file=sys.stderr)
    (destination.parent / "execution.json").write_text(
        json.dumps(
            {
                "milestone": "m2",
                "started_at_utc": started,
                "finished_at_utc": datetime.now(UTC).isoformat(),
                "exit_code": result.returncode,
                "produced_junit": xml is not None,
                "junit_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()
                if xml
                else None,
            },
            indent=2,
        )
        + "\n"
    )
    sys.exit(result.returncode if result.returncode else (0 if xml else 1))


if __name__ == "__main__":
    main()
