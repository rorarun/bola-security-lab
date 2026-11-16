# BOLA Security Lab

**Detecting and Preventing Broken Object-Level Authorization in a Collaborative Task Management API**

COMP 3123 — Computer Security, Fall 2026. Submission: November 24, 2026.

This is a synthetic, local research laboratory, not a general-purpose scanner.
**Current milestone: M3-A authorization evaluation framework.** The M2 API remains defensive.
Authentication, organizations, projects, memberships and
task CRUD are implemented with endpoint-specific authorization. Owner/editor/viewer permissions,
current membership, tenant boundaries and parent relationships are checked server-side.
The safe `hardened` default currently selects this defensive endpoint-specific implementation;
it does not claim centralized enforcement. Explicit `endpoint` mode requires lab environment and
opt-in. The vulnerable baseline remains unavailable; centralized authorization and the full
three-configuration experiment remain deferred.

## Local setup

Requires Docker Engine and Compose v2. From the repository root:

```sh
docker compose config --quiet
docker compose up -d --build --wait api
docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready').read().decode())"
docker compose run --rm -e BOLA_LAB_OPT_IN=true migrate bola-lab seed
docker compose exec -T api python - < scripts/demo_auth.py
```

Compose starts PostgreSQL, applies checksummed migrations, then starts the API. The API is published
only at `127.0.0.1:8000`; PostgreSQL has no published host port. The network is internal. Do not add
public tunnels, host networking, or public port mappings. Seed refuses a populated database;
`bola-lab seed --reset` explicitly destroys and replaces lab records and sessions.

Interactive API documentation: <http://127.0.0.1:8000/docs>.
See [setup and fixtures](docs/setup.md), [API contract](docs/api.md),
[collaboration demonstration](docs/demonstration.md), and [M2 verification](docs/m2-verification.md).
The cloud build required a temporary CA
secret adaptation documented there; normal Docker trust settings remain unchanged.

## Tests

```sh
docker compose up -d --wait db
docker compose exec -T db createdb -U bola_lab bola_lab_test
docker compose --profile test build test
docker compose --profile test run --rm test
python3 scripts/verify_api.py
```

Create the disposable test database once; `createdb` errors if it already exists. Tests erase its
application tables, not the normal `bola_lab` database. Integration fixtures require an explicit local
`BOLA_TEST_DATABASE_URL` and database name ending in `_test`. Without that variable, integration
checks explicitly skip; this is not full verification. `verify_api.py` runs the current suite
and preserves JUnit in `results/m2/`. CI supplies PostgreSQL and runs lint and tests.
Historical M1 evidence remains in `results/m1/` and the `feature/m1-foundation` branch.

Stop with `docker compose down` (retains data). `docker compose down -v` also deletes the lab volume.

## Research scope

- [Approved requirements and milestones](docs/requirements.md)
- [Full permission matrix](docs/permission-matrix.md)
- [Architecture and schema diagrams](docs/architecture.md)
- [Threat model and boundaries](docs/threat-model.md)
- [Experiment methodology and planned inventories](docs/experiment-plan.md)
- [Evidence status](results/README.md)
- [M3-A methodology](docs/evaluation/methodology.md), [frozen scenarios](docs/evaluation/scenarios.md),
  [defect-class mapping](docs/evaluation/defect-inventory.md), and [reproduction](docs/evaluation/reproduction.md)
- [Actual M3-A verification and evidence](docs/evaluation/verification.md)

M3-A evaluates 56 independently specified scenarios against the existing API using a harness-owned
loopback HTTP server and `bola_lab_evaluation_test`. It adds no authorization configuration or seeded
vulnerability. Start with the reproduction guide; existing output directories are never overwritten.
Reports derive from checksummed observations and explicitly identify incomplete runs. Seeded-defect
recall remains unavailable until a labelled defective configuration is separately authorized and run.
The initial v1 oracle-ordering failure and its explicit v2 amendment are preserved for transparency.

Only synthetic records and local targets are permitted. A private repository does not make a
vulnerable service safe. M2 rejects baseline startup even with laboratory opt-in.
No public deployment workflow is included.

The final academic report must be at least eight pages; the recording must be no longer than ten
minutes. The user authors those separately. Research evidence takes priority over optional frontend,
latency measurements, identifier-format comparisons, and portfolio extras.
