# Setup and synthetic fixtures

Use the Compose commands in the README for the normal local workflow. Images are version-tagged;
Python dependencies are pinned transitively in `requirements.lock` and `requirements-dev.lock`.
Build backend is pinned in `pyproject.toml`. Image tags are not immutable digests; the verification
manifest records images used. Never introduce real accounts or passwords.

## Python development

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
ruff check .
ruff format --check .
```

Direct Python operation requires `BOLA_DATABASE_URL` with an explicit PostgreSQL host and database.
Do not publish the Compose database merely for development: run the suite in its test container.
CLI: `bola-lab migrate`, `bola-lab seed [--reset]`, `bola-lab serve`.
Default environment is `production`, mode `hardened`, bind/publish host loopback and token TTL 900s.
Seeding requires `BOLA_ENVIRONMENT=lab` and `BOLA_LAB_OPT_IN=true` together. Compose sets lab environment
but defaults opt-in false. `.env.example` is for Compose interpolation; Python does not auto-load `.env`.
M1 always rejects `baseline` and `endpoint` modes, including valid local opt-in.

## Fixture version 1

All seed accounts use **Synthetic-Lab-Only-2026!**, a public synthetic password for this lab only.

| User ID | Email | Membership |
|---|---|---|
| 1 | owner@alpha.example | Alpha organization; owner of project 1 |
| 2 | editor@alpha.example | Alpha organization; editor of project 1 |
| 3 | viewer@alpha.example | Alpha organization; viewer of project 1 |
| 4 | outsider@alpha.example | Alpha organization; no projects |
| 5 | owner@beta.example | Beta organization; owner of project 3 |
| 6 | removed@alpha.example | Alpha organization; no projects; reserved for later revocation scenarios |
| 7 | second-owner@alpha.example | Alpha organization; owner of project 2 |

Organizations 1/2 are Alpha/Beta. Projects 1/2 belong to Alpha; project 3 belongs to Beta.
Task IDs 1/2/3 belong respectively to projects 1/2/3. Each starts with status `todo` and title
`Synthetic task <id>`. Logical content and timestamps are fixed. Password salts and sessions are random.
Identity sequences advance past fixture IDs. No fixture implies that revocation behavior is already
implemented or evaluated through resource endpoints.

## Cloud proxy build workaround used for M1

The standard Docker build failed certificate verification inside the base image in this managed
environment. TLS was not disabled. An ephemeral Dockerfile added a CA secret mount to pip steps:

```sh
python - <<'PY'
from pathlib import Path
text = Path('Dockerfile').read_text().replace(
    'RUN pip ',
    'RUN --mount=type=secret,id=proxy_ca,required=true PIP_CERT=/run/secrets/proxy_ca pip ',
)
Path('/tmp/bola-m1.Dockerfile').write_text(text)
PY
docker build -f /tmp/bola-m1.Dockerfile \
  --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt \
  --target runtime -t bola-security-lab-api -t bola-security-lab-migrate .
docker build -f /tmp/bola-m1.Dockerfile \
  --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt \
  --target test -t bola-security-lab-test .
docker compose up -d --no-build --wait api
```

This workaround is specific to an environment with that CA bundle and Docker BuildKit. CA contents
are not copied into image layers or committed. Use your environment's documented CA source if different.
In this cloud sandbox, uv also needed `UV_CACHE_DIR=/tmp/bola-uv-cache` because the home cache is read-only.
