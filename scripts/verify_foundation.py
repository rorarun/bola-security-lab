"""Run the real Compose suite and preserve JUnit outside its ephemeral filesystem."""

import re
import subprocess
import sys
from pathlib import Path


def main():
    if Path("src/bola_lab/endpoint_api.py").exists():
        raise SystemExit(
            "M1 evidence is frozen. Checkout feature/m1-foundation for M1, "
            "or run scripts/verify_api.py for M2."
        )
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
    if xml:
        destination = Path("results/m1/junit.xml")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(xml.group() + "\n")
        print(result.stdout[: xml.start()] + result.stdout[xml.end() :])
        print(f"Preserved {destination}")
    else:
        print(result.stdout)
        print("JUnit was not produced; verification is incomplete.", file=sys.stderr)
    sys.exit(result.returncode if result.returncode else (0 if xml else 1))


if __name__ == "__main__":
    main()
