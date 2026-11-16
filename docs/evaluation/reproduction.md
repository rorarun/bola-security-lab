# Reproduce M3-A locally

Requirements: Docker/Compose, Python 3.12 and the existing development environment (`pip install
-r requirements-dev.lock`, then `pip install --no-deps -e .`). No new dependencies are required.

From the repository root, start PostgreSQL and create the disposable evaluation DB once:

```sh
docker compose up -d --wait db
docker compose exec -T db createdb -U bola_lab bola_lab_evaluation_test
docker compose --profile test build test
```

The existing lab network and published ports remain unchanged. Do not publish a database port.
The usual cloud CA-secret build adaptation in setup.md may be needed in the managed environment.
Choose a new output directory for each execution; the wrapper refuses to overwrite prior evidence:

```sh
export BOLA_EVALUATION_DATABASE_URL='postgresql://bola_lab:synthetic-local-only@db:5432/bola_lab_evaluation_test'
.venv/bin/python scripts/run_evaluation.py --output results/m3a/runs/local-001
```

That credential is an existing public synthetic local value, not a private secret. Do not display
environment variables or actual tokens in academic screenshots. The runner resets only the named
evaluation database. Existing M2 app/regression databases and fixture records are unaffected.

The host wrapper runs the existing test container, extracts only regular top-level evidence files,
and verifies the image's source/test/migration hashes against the checkout. The child server and
its temporary listener live inside that container. There is no need for a host-published API port.

For native development/CI with an already-created local evaluation database, set its explicit DSN
and run the module directly:

```sh
python -m bola_lab.evaluation.runner --output results/m3a/runs/native-001
```

Regenerate all derived outputs without issuing any HTTP requests:

```sh
.venv/bin/python -m bola_lab.evaluation.reports results/m3a/runs/local-001
```

The report generator verifies raw observations, inventory and fixture checksums before processing.
It uses the inventory copy preserved with that run, not mutable current expectations. Summary JSON,
evaluations JSON, CSV, JUnit and Markdown regenerate byte-for-byte from the same inputs.

Run all existing regressions and framework unit/calibration tests with the existing Compose test
service after creating `bola_lab_test` once as described in the main README:

```sh
docker compose --profile test run --rm test
```

CI runs regressions, creates a separate evaluation database, executes all frozen live scenarios,
checks report regeneration, and uploads sanitized evidence even if a verification step fails.
Inspect completeness/errors and process exit status before citing any rates. Setup failures create
unrun/inconclusive observations, not fictitious successful cases.
