# BOLA Security Lab

**Detecting and Preventing Broken Object-Level Authorization in a Collaborative Task Management API**

COMP 3123 — Computer Security, Fall 2026. Submission: November 24, 2026.

This is a synthetic, local research laboratory, not a general-purpose scanner.
**Current milestone: M1 foundation only.** Authentication, schema, seed data, safeguards, tests and
initial CI are implemented. Project/task endpoints and the three experimental authorization
implementations are deferred. The `hardened` default is a reserved configuration name, not a claim
that the future task API has already been implemented or evaluated.

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
See [setup and fixtures](docs/setup.md), [authentication demonstration](docs/demonstration.md), and
[actual verification results](docs/m1-verification.md). The cloud build required a temporary CA
secret adaptation documented there; normal Docker trust settings remain unchanged.

## Tests

```sh
docker compose up -d --wait db
docker compose exec -T db createdb -U bola_lab bola_lab_test
docker compose --profile test build test
docker compose --profile test run --rm test
```

Create the disposable test database once; `createdb` errors if it already exists. Tests erase its
application tables, not the normal `bola_lab` database. Integration fixtures require an explicit local
`BOLA_TEST_DATABASE_URL` and database name ending in `_test`. Without that variable, integration
checks explicitly skip; this is not full verification. CI supplies PostgreSQL and runs lint and tests.

Stop with `docker compose down` (retains data). `docker compose down -v` also deletes the lab volume.

## Research scope

- [Approved requirements and milestones](docs/requirements.md)
- [Full permission matrix](docs/permission-matrix.md)
- [Architecture and schema diagrams](docs/architecture.md)
- [Threat model and boundaries](docs/threat-model.md)
- [Experiment methodology and planned inventories](docs/experiment-plan.md)
- [Evidence status](results/README.md)

Only synthetic records and local targets are permitted. A private repository does not make a
vulnerable service safe. M1 rejects non-hardened configurations even with laboratory opt-in.
No public deployment workflow is included.

The final academic report must be at least eight pages; the recording must be no longer than ten
minutes. The user authors those separately. Research evidence takes priority over optional frontend,
latency measurements, identifier-format comparisons, and portfolio extras.
