# BOLA Security Lab

### Detecting and Preventing Broken Object-Level Authorization in a Collaborative Task Management API

**Course:** COMP 3123 — Computer Security  
**University:** Acadia University  
**Academic Term:** Fall 2026  
**Project Type:** API Security Research and Experimental Evaluation

## 1. Project Overview

BOLA Security Lab is a research project that investigates **Broken Object-Level Authorization (BOLA)** in a collaborative task-management API.

BOLA occurs when an API fails to verify whether an authenticated user is authorized to access or modify a particular resource. An attacker may exploit this weakness by changing resource identifiers in API requests to access another user's data or perform unauthorized operations.

This project implements a task-management backend using Python, FastAPI, and PostgreSQL. It supports organizations, projects, users, memberships, and tasks.

The main objective is to investigate how automated, multi-identity security testing can detect deliberately introduced BOLA vulnerabilities and evaluate the effectiveness of two defensive authorization approaches.

The study compares three implementations:

1. **Vulnerable baseline:** A deliberately flawed implementation used only in a controlled, isolated laboratory.
2. **Endpoint-specific authorization:** Authorization decisions implemented within individual API endpoint handlers.
3. **Centralized authorization:** Authorization decisions enforced through a shared policy/service layer with scoped database operations.

All three treatments are evaluated against the same security expectations and synthetic test scenarios.

## 2. Research Questions

This project investigates two primary questions:

- How effectively can automated tests using multiple authenticated identities detect known, deliberately seeded BOLA vulnerabilities?
- Can endpoint-specific and centralized authorization prevent unauthorized operations while preserving legitimate collaboration?

The experiment also examines whether either defensive approach demonstrates measurable security advantages within the selected test scenarios.

## 3. Technologies Used

| Component | Technology |
|---|---|
| Programming language | Python 3.12 |
| API framework | FastAPI |
| API server | Uvicorn |
| Database | PostgreSQL 17 |
| Database connectivity | Psycopg 3 |
| Validation | Pydantic |
| Password security | Argon2id |
| API testing | pytest and HTTPX |
| Code quality | Ruff |
| Containerization | Docker and Docker Compose |
| Continuous integration | GitHub Actions |
| Data visualization | Matplotlib |
| API documentation | Swagger UI / OpenAPI |

The project uses version-controlled dependency lockfiles and SQL migrations to improve reproducibility.

## 4. Implemented Features

### Authentication and Session Management

- User registration and login
- Password hashing using Argon2id
- Short-lived opaque bearer tokens
- Token revocation and session expiration
- Authenticated user identity verification
- Server-side session validation

### Collaborative Task Management

- Create and manage organizations
- Create and manage projects
- Add, update, and remove project memberships
- Create, list, read, update, and delete tasks
- Assign owner, editor, and viewer permissions
- Enforce organization and project boundaries
- Restrict operations based on current membership

### Authorization Permissions

| Role | Read Tasks | Create Tasks | Update Tasks | Delete Tasks | Manage Memberships |
|---|---|---|---|---|---|
| Owner | Yes | Yes | Yes | Yes | Yes |
| Editor | Yes | Yes | Yes | No | No |
| Viewer | Yes | No | No | No | No |
| Outsider | No | No | No | No | No |

Permissions are checked on the server, not trusted from client-submitted role information.

## 5. Project Architecture

The standard defensive application follows this general architecture:

```text
Client / Swagger UI
        |
        v
   FastAPI REST API
        |
        v
 Authentication Layer
        |
        v
 Authorization Layer
        |
        v
 PostgreSQL Database
```

### Endpoint-Specific Authorization

In the endpoint-specific implementation, each protected route performs its own authorization checks before accessing or modifying the requested resource.

**Source:** `src/bola_lab/endpoint_api.py`

### Centralized Authorization

In the centralized implementation, API handlers delegate operations to a shared service and policy layer. Database operations use resource scope restrictions.

**Important source files:**

- `src/bola_lab/central_api.py`
- `src/bola_lab/central_service.py`
- `src/bola_lab/policy.py`
- `src/bola_lab/scoped_repository.py`

The standard `hardened` application mode selects the centralized implementation. An explicitly selected `endpoint` mode is also available in the local laboratory environment.

### Vulnerable Baseline

The deliberately vulnerable implementation is maintained separately under:

`laboratory/`

It contains five identified BOLA defects for controlled research. It is not available as a normal public API deployment mode.

## 6. Investigated BOLA Vulnerabilities

Five vulnerabilities were deliberately introduced into the isolated research baseline.

| ID | Vulnerability | Description |
|---|---|---|
| B01 | Unauthorized task detail access | A user may retrieve a task without the required object-level authorization check |
| B02 | Task list information disclosure | A task-list query may return records outside the caller's permitted scope |
| B03 | Unauthorized task modification | A user may modify a task without appropriate membership or action permissions |
| B04 | Unauthorized task deletion | A user may delete a task without the required ownership and authorization checks |
| B05 | Unauthorized task creation | A user may create a task in a project without sufficient permission |

These vulnerabilities are intentionally restricted to the synthetic laboratory to support security testing and countermeasure evaluation.

## 7. Experimental Methodology

The final study compared three authorization treatments under a controlled test design.

Each treatment executed:

- 56 core security scenarios
- 6 supplemental scenarios

**Total: 62 observations per treatment, producing 186 observations across all three treatments.**

The tests covered:

- Authentication and session handling
- Authorized task operations
- Unauthorized reads and writes
- Project membership restrictions
- Cross-organization access
- Task and project identifier manipulation
- Resource-parent mismatches
- Membership changes and revocation
- Response contents and persisted database effects

Expected behavior was defined independently of each implementation's authorization code.

The evaluation recorded actual HTTP responses, authorization outcomes, selected database state changes, execution errors, and detector findings.

## 8. Experimental Results

The final comparative experiment was executed on November 16, 2026.

### Core Security Results

| Metric | Vulnerable Baseline | Endpoint-Specific | Centralized |
|---|---:|---:|---:|
| Authorization enforcement accuracy | 24/47 (51.1%) | 47/47 (100%) | 47/47 (100%) |
| Unauthorized operation success | 21/29 (72.4%) | 0/29 (0%) | 0/29 (0%) |
| Legitimate operation success | 16/18 (88.9%) | 18/18 (100%) | 18/18 (100%) |
| Detector false positives on selected controls | 0/16 | 0/16 | 0/16 |
| Detection recall for verified seeded defects | 5/5 (100%) | Not applicable | Not applicable |

### Key Findings

**Finding 1: The detector identified all five seeded defect classes.**

The detector achieved 5/5 recall against independently verified, known-present vulnerabilities in the experimental baseline.

This result applies only to the selected seeded vulnerabilities. It does not establish accuracy against unknown real-world vulnerabilities.

**Finding 2: Both defensive implementations prevented unauthorized operations in the core test set.**

Neither endpoint-specific nor centralized authorization permitted any of the 29 tested prohibited operations.

**Finding 3: Both defensive implementations preserved legitimate functionality.**

Each defensive implementation successfully completed all 18 tested legitimate operations.

**Finding 4: The defensive implementations had identical measured outcomes.**

The experiment did not demonstrate superior authorization enforcement by centralized authorization compared with correctly implemented endpoint-specific authorization.

Centralization may offer organizational or maintainability advantages, but such advantages were not established by these security measurements.

### Supplemental Evaluation

An additional six scenarios were executed per treatment. The endpoint-specific and centralized implementations satisfied all six expected outcomes; the baseline satisfied four.

Full supplemental counts are preserved separately in the machine-readable comparison results.

## 9. Run the Application Locally

### Requirements

- Docker Desktop with Docker Compose
- A web browser
- Git (if cloning the repository)
- Python 3.12 for running the study wrapper and development tools

The standard application is designed to run locally and must not be exposed to the public internet.

### Step 1 — Obtain the Source Code

Clone the repository or download the source ZIP from GitHub.

```bash
git clone https://github.com/rorarun/bola-security-lab.git
cd bola-security-lab
```

**Note:** This repository is private. Cloning requires authorized GitHub access.

### Step 2 — Start Docker Desktop

Start Docker Desktop and confirm that its Docker engine is running.

### Step 3 — Build and Start the Application

Run the following commands in the repository root:

```powershell
docker compose config --quiet
docker compose up -d --build --wait api
```

Docker Compose starts PostgreSQL, applies database migrations, and launches FastAPI.

Verify that the services are running:

```powershell
docker compose ps
```

### Step 4 — Open Swagger UI

Open the following address in a browser:

**http://127.0.0.1:8000/docs**

The API documentation provides an interactive interface for authentication, organization management, project management, and task operations.

The root path `/` is not a graphical homepage. A `404 Not Found` response at that path does not indicate that the API has failed.

### Windows Networking Note

In one tested Windows Docker Desktop environment, the API container became healthy but the host port was not accessible while attached only to the isolated laboratory network.

For a local demonstration, create a file named `compose.demo.yaml` in the repository root with the following content:

```yaml
services:
  api:
    networks:
      - lab
      - demo

networks:
  demo:
    driver: bridge
```

Then launch the defensive application with:

```powershell
docker compose -f compose.yaml -f compose.demo.yaml up -d --build --wait api
```

This supplies an additional bridge network to the defensive API. The original Compose port mapping remains restricted to `127.0.0.1:8000`. The database remains on the laboratory network without a published database port.

Use this configuration for local demonstrations only. Do not use it to expose the deliberately vulnerable baseline.

### Step 5 — Load Synthetic Data

For a fresh database, run:

```powershell
docker compose run --rm -e BOLA_LAB_OPT_IN=true migrate bola-lab seed
```

This creates synthetic users, organizations, memberships, projects, and tasks.

If the database is already populated, the command intentionally refuses to overwrite existing records.

Do not use `--reset` unless you explicitly intend to destroy and replace disposable laboratory data.

## 10. Demonstration Accounts

All seeded accounts share the synthetic laboratory password:

`Synthetic-Lab-Only-2026!`

| Account | Demonstration Role |
|---|---|
| owner@alpha.example | Owner of Alpha Project 1 |
| editor@alpha.example | Editor of Alpha Project 1 |
| viewer@alpha.example | Viewer of Alpha Project 1 |
| outsider@alpha.example | Alpha organization member without Project 1 access |
| owner@beta.example | Owner of Beta Project 3 |

These are intentionally synthetic accounts and credentials. They must never be reused for real services.

### Example Security Demonstration

**Scenario A — Authorized task access**

Authenticate as an authorized member of Alpha Project 1.

Request:

```http
GET /organizations/1/projects/1/tasks/1
```

Expected response: `200 OK`, showing the task's details.

**Scenario B — Unauthorized task modification**

Authenticate as `viewer@alpha.example`.

Request:

```http
PATCH /organizations/1/projects/1/tasks/1
```

Request body:

```json
{
  "title": "Unauthorized modification attempt"
}
```

Expected response:

```json
{
  "detail": "Insufficient project role"
}
```

HTTP status: `403 Forbidden`.

A subsequent authorized GET request should confirm that the original task remains unchanged.

**Scenario C — Cross-Organization Access**

While authenticated as `viewer@alpha.example`, request:

```http
GET /organizations/2/projects/3/tasks/3
```

Expected response:

```json
{
  "detail": "Resource not found"
}
```

HTTP status: `404 Not Found`.

This prevents an unauthorized user from retrieving a task belonging to another organization.

For a complete demonstration, authenticate as `owner@beta.example` and verify that the same task can be retrieved successfully with HTTP `200 OK`.

### Automated Collaboration Demonstration

The repository also includes a script that performs real local HTTP requests across multiple authenticated identities:

```powershell
Get-Content scripts/demo_collaboration.py -Raw | docker compose exec -T api python -
```

The script exercises authorized and prohibited operations and checks their outcomes.

It uses synthetic data and avoids printing raw bearer tokens.

## 11. Running Automated Tests

The project contains automated tests for authentication, database operations, resource permissions, evaluation logic, and research safety requirements.

Test execution uses a separate, disposable PostgreSQL test database.

Follow the repository setup and evaluation documentation before running the full suite:

- `docs/setup.md`
- `docs/evaluation/reproduction.md`

GitHub Actions also runs automated testing and code-quality checks.

The final study branch passed GitHub Actions at commit `4a28acf`.

**GitHub CI verifies the configured regression and evaluation checks; the workflow does not currently rerun the complete three-treatment M5 study.**

## 12. Research Evidence and Reproducibility

The final experiment evidence is available at:

[`results/m5-comparison-20261116/`](results/m5-comparison-20261116/)

### Main Evidence Files

| File | Purpose |
|---|---|
| `comparison.md` | Readable experimental summary |
| `comparison.json` | Structured quantitative results |
| `manifest.json` | Source provenance, environment information, hashes, and timestamps |
| `baseline/` | Vulnerable baseline observations and metrics |
| `endpoint/` | Endpoint-specific authorization observations and metrics |
| `centralized/` | Centralized authorization observations and metrics |
| `confirmed-violations.png` | Visualization of confirmed security violations |
| `operation-outcomes.png` | Comparison of operation outcomes |
| `distinct-defect-detection.png` | Visualization of detected seeded defect classes |

The evidence also includes frozen test inventories, synthetic fixtures, checksums, raw observations, and individual treatment reports.

### Reproducing the Complete Study

The study runner is:

`scripts/run_evaluation.py`

The complete experiment is selected using its `--study` argument.

Reproduction requires:

1. Python 3.12 with the development dependencies installed.
2. Docker Compose and the test container image.
3. A dedicated disposable PostgreSQL database named `bola_lab_evaluation_test`.
4. The explicit `BOLA_EVALUATION_DATABASE_URL` setting.
5. A new output directory for every run.

The evaluation database must be separate from the normal application database.

See the study runner and the reproduction documentation for database setup and execution details. Never point the evaluation runner at real user data.

### Source Provenance

The original final comparative run was performed from a working tree containing uncommitted source changes.

The preserved manifest identifies commit `5369ac9`, records the dirty-worktree state, and includes SHA-256 digests of the evaluated source files.

The corresponding evaluated implementation was subsequently committed as `583a542`. Its original experiment evidence was preserved in commit `4a28acf`.

These details are retained for transparency rather than retroactively rewriting the experimental provenance.

## 13. Project Structure

```text
bola-security-lab/
|
|-- src/bola_lab/
|   |-- main.py
|   |-- auth.py
|   |-- endpoint_api.py
|   |-- central_api.py
|   |-- central_service.py
|   |-- policy.py
|   |-- scoped_repository.py
|   |-- evaluation/
|
|-- laboratory/
|   |-- app.py
|   |-- witness.py
|
|-- migrations/
|-- tests/
|-- scripts/
|-- docs/
|-- results/
|   |-- m1/
|   |-- m2/
|   |-- m3a/
|   |-- m5-comparison-20261116/
|
|-- compose.yaml
|-- Dockerfile
|-- pyproject.toml
|-- README.md
```

Earlier milestone documentation and results remain preserved to document the project's development history.

## 14. Limitations

This project is an academic security research laboratory, not a production-ready application or unrestricted vulnerability scanner.

The following limitations apply:

- Tests use synthetic accounts, organizations, projects, and tasks.
- Evaluation covers a finite, predetermined collection of scenarios.
- The five seeded vulnerabilities are known and deliberately introduced.
- The reported detection recall does not measure performance against unknown vulnerability classes.
- False-positive measurements are limited to selected compliant controls.
- The study does not establish that centralized authorization is universally more secure than endpoint-specific authorization.
- The experiment does not provide a broad concurrency, latency, scalability, or penetration-testing evaluation.
- Source and evaluation components were developed within the same project, limiting independent generalizability.

The reported findings should therefore be interpreted as outcomes of a controlled experimental comparison rather than guarantees of security in production systems.

## 15. Security and Responsible Use

This repository contains deliberately vulnerable code for educational research.

The vulnerable baseline must remain isolated in a controlled local environment and must not be deployed publicly.

The project is intended only for testing synthetic resources and systems under the project owner's control.

Do not use the experimental tooling to probe third-party services without authorization.

## 16. Conclusion

The BOLA Security Lab demonstrates how object-level authorization weaknesses can arise in collaborative APIs and how automated, multi-identity tests can detect known authorization failures.

The controlled experiment detected all five seeded baseline defects. Both defensive implementations prevented the 29 tested unauthorized core operations while preserving all 18 tested legitimate operations.

The results support the importance of consistent server-side object authorization, resource scoping, and automated security regression testing.

They do not establish that one correct defensive architecture is universally superior to the other.

## 17. References and Further Reading

- [OWASP API Security Top 10 (2023)](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)
- [OWASP API1:2023 — Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
- [MITRE CWE-639 — Authorization Bypass Through User-Controlled Key](https://cwe.mitre.org/data/definitions/639.html)
- [MITRE CWE-862 — Missing Authorization](https://cwe.mitre.org/data/definitions/862.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

**Disclaimer:** This project is intended for computer security education and controlled research. All deliberately vulnerable components must remain isolated from public networks.
