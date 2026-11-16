"""Use the existing test container; safely preserve its ephemeral M3-A evidence on the host."""

import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path


def main():
    from bola_lab.evaluation.models import source_hashes

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--study", action="store_true", help="Run the complete three-treatment study"
    )
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Choose a new evidence directory; existing evidence is never overwritten")
    if not os.environ.get("BOLA_EVALUATION_DATABASE_URL"):
        raise SystemExit(
            "Set BOLA_EVALUATION_DATABASE_URL to the dedicated synthetic evaluation database"
        )
    environment = dict(os.environ)
    environment["BOLA_EVALUATION_SOURCE_COMMIT"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    environment["BOLA_EVALUATION_SOURCE_DIRTY"] = (
        "true" if subprocess.check_output(["git", "status", "--porcelain"]) else "false"
    )
    command = ["docker", "compose", "--profile", "test", "run", "--rm"]
    for key in (
        "BOLA_EVALUATION_DATABASE_URL",
        "BOLA_EVALUATION_SOURCE_COMMIT",
        "BOLA_EVALUATION_SOURCE_DIRTY",
    ):
        command += ["-e", key]
    command += [
        "test",
        "python",
        "-m",
        "bola_lab.evaluation.study" if args.study else "bola_lab.evaluation.runner",
        "--output",
        "/tmp/m3a-run",
        "--stream-archive",
    ]
    result = subprocess.run(command, env=environment, capture_output=True, text=True)
    match = re.search(r"BOLA_EVIDENCE_BEGIN\n([A-Za-z0-9+/=\n]+)\nBOLA_EVIDENCE_END", result.stdout)
    if not match:
        # Do not echo arbitrary subprocess diagnostics which could contain environment details.
        raise SystemExit(
            "Evaluation failed before producing evidence; no results claimed (exit code "
            + str(result.returncode)
            + ")"
        )
    args.output.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(match[1])), mode="r:gz") as archive:
        for item in archive.getmembers():
            relative = Path(item.name)
            if (
                not item.isfile()
                or relative.is_absolute()
                or ".." in relative.parts
                or item.name in {".", ".."}
            ):
                raise ValueError("Unsafe evidence archive member")
            data = archive.extractfile(item).read()
            target = args.output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    manifest = json.loads((args.output / "manifest.json").read_text())
    actual_source = (manifest.get("source") or {}).get("source_sha256")
    if actual_source != source_hashes(Path.cwd()):
        raise SystemExit(
            "Image source does not match checkout; evidence retained but verification rejected"
        )
    metrics = json.loads(
        (args.output / ("comparison.json" if args.study else "metrics.json")).read_text()
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "counts": metrics["counts"],
                "run_passed": metrics["run_passed"],
            },
            indent=2,
        )
    )
    sys.exit(result.returncode if result.returncode else (0 if metrics["run_passed"] else 1))


if __name__ == "__main__":
    main()
