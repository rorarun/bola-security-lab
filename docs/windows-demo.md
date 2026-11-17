# Windows Local Demonstration

## Requirements

- Windows 10/11
- Docker Desktop with a running Docker engine
- Docker Compose
- The BOLA Security Lab repository

## Start the API

From the project root:

```powershell
docker compose config --quiet
docker compose up -d --build --wait api
```

If the API container is healthy but port 8000 is not accessible on Windows, create a separate, local-only Compose configuration named `compose.demo.yaml`:

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

Start the local demonstration configuration:

```powershell
docker compose -f compose.yaml -f compose.demo.yaml up -d --build --wait api
```

Do not expose the API publicly or run the deliberately vulnerable baseline as a public service.

## Load Synthetic Data

On a fresh database:

```powershell
docker compose run --rm -e BOLA_LAB_OPT_IN=true migrate bola-lab seed
```

Do not use `--reset` unless intentionally replacing disposable lab data.

## Open Swagger UI

Visit:

http://127.0.0.1:8000/docs

## Demonstration Accounts

All accounts use the repository's synthetic laboratory password.

- `owner@alpha.example`
- `editor@alpha.example`
- `viewer@alpha.example`
- `owner@beta.example`

## Suggested Security Demonstration

1. Authenticate as the Alpha project owner and read Task 1.
2. Authenticate as the Alpha viewer and confirm that reading Task 1 is allowed.
3. Attempt to update Task 1 as the viewer. Expected: HTTP 403.
4. Attempt to read Task 3 in Beta Organization as the Alpha viewer. Expected: HTTP 404.
5. Authenticate as the Beta owner and verify that Task 3 is accessible. Expected: HTTP 200.

The demonstration should confirm authorization outcomes and unchanged data after rejected writes.

## Stop the Environment

For the standard configuration:

```powershell
docker compose down
```

For the demonstration override:

```powershell
docker compose -f compose.yaml -f compose.demo.yaml down
```

Do not run `docker compose down -v` unless intentionally deleting the synthetic PostgreSQL data volume.
