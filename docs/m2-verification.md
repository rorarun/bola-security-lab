# M2 verification: functional collaboration with endpoint-specific authorization

M1 was preserved first on `feature/m1-foundation`, commit
`7047806e2e60e33efa8222eb6aeb6ffdc8f3be99`. Its 58-test rerun and hosted Actions run 43651119476
both succeeded. See m1-review.md for secret/artifact review, ownership guarantees and remote checks.
M2 branches independently as `feature/m2-task-api`; no merge into main is authorized or performed.

## Implemented behavior and decisions

Organizations can be created, listed and read by their members. Organization members create projects
and become their sole owners. Project membership governs project visibility and all protected
operations. Owners manage project, memberships and tasks; editors create/read/update tasks; viewers
read. Organization member provisioning is a local opt-in CLI, not a public HTTP operation.

Resource request models reject unknown ownership/tenant/creator fields, invalid roles/statuses,
empty patches, explicit null patches and invalid bigint identifiers. Creators come from validated
sessions, not client bodies. Response models omit internal membership lookup context.

Endpoint functions explicitly decide scope and actions; repository functions contain reusable
SQL/business operations without granting permissions. The safe `hardened` default invokes the
defensive endpoint-specific implementation during M2; explicit `endpoint` requires lab opt-in.
There is no centralized implementation or vulnerable baseline. Baseline startup remains rejected
even with valid local lab opt-in. No full BOLA experiment runner was added.

The M1 schema/migration is unchanged. Organization+creator membership and project+owner membership
commit atomically. Per-project write locks precede fresh membership reads. Owner deletion/demotion
is rejected in both API and database. Project deletion legitimately cascades only its children.

## Actual local results

| Test group | Passed | Failed/errors/skipped |
|---|---:|---:|
| Authentication contract/storage | 18 | 0 |
| PostgreSQL migrations/integrity/seed | 17 | 0 |
| Resource collaboration/authorization/transactions | 149 | 0 |
| Configuration/deployment safeguards | 23 | 0 |
| **Total** | **207** | **0** |

The full final execution used real PostgreSQL 17.7, Python 3.12.12 and pinned dependencies inside
the test image. It completed in approximately 53 seconds. The earlier 200-case run also passed;
the final run adds collection authentication, permission promotion and actual CLI provisioning,
and strengthens parent mismatch cases with a caller belonging to both organizations.

Assertions check exact permitted list IDs/content, returned creator/tenant relationships, committed
values, unrelated rows, unchanged domain state on denials, and rollback after injected errors
following organization/project/task inserts. Revocation/downgrade and promotion reuse the same
unexpired tokens; `/users/me` remains valid after project access is revoked. Tests specify expected
roles/outcomes independently rather than using production authorization functions as an oracle.

Ruff lint/formatting, whitespace checks and rendered Compose validation passed. Runtime and test
images built using the previously documented cloud CA-secret adaptation with TLS enabled. Updated
API startup/readiness succeeded. The real-HTTP demo passed with 19 sanitized request/response records:
owner project/membership creation, editor task creation/update, viewer read, viewer update/editor
delete denials, both outsiders denied, proven parent mismatch, exact list, revocation, and cleanup.
There were no failing application tests. Formatting findings were corrected, not suppressed.

## Evidence and reproduction

From a fresh checkout of the M2 branch, using Docker/Compose and Python 3:

```sh
docker compose config --quiet
docker compose up -d --build --wait api
docker compose run --rm -e BOLA_LAB_OPT_IN=true migrate bola-lab seed
docker compose exec -T api python - < scripts/demo_collaboration.py
docker compose exec -T db createdb -U bola_lab bola_lab_test
docker compose --profile test build test
python3 scripts/verify_api.py
python3 scripts/record_foundation.py results/m2/junit.xml results/m2/manifest.json --milestone m2
```

Seed requires an empty lab database; test DB creation is once only. Do not reset existing data
unintentionally. See setup.md for the managed cloud certificate adaptation and container-only HTTP
verification. Keep loopback publication; do not broaden it to compensate for the cloud limitation.

`results/m2/junit.xml` preserves the 207 case outcomes. `execution.json` records exit status and XML
checksum. `manifest.json` records source hashes (including dirty source when not yet committed),
exact tested-image source equality, image IDs, dependency/PostgreSQL versions and implementation
identity. `demo.json` preserves actual sanitized resource requests/responses, not fabricated examples.
Raw credentials and issued tokens are excluded. Historical M1 evidence is not overwritten.
The later commit binds this verified source snapshot; use `git rev-parse HEAD` for the checkout SHA.
Hosted CI outcomes must be checked for the exact pushed SHA in GitHub Actions, independently of
the local evidence. The workflow uploads its actual JUnit artifact; this report does not infer
hosted success from local tests.

## Limitations and stopping boundary

One Starlette warning reports deprecation of its HTTPX TestClient integration; it is not suppressed.
Cloud host-loopback curl remained unavailable in M1; M2 live HTTP was verified within the API
container. The ordinary non-proxy Docker build still requires verification in the user's own
environment. Lab administration credentials, no TLS, no brute-force protections, unpaginated small
synthetic lists and no account verification make this a local research application, not a production
deployment. Broad overlapping-request/load behavior has not been exhaustively tested; no timing or
security generalization follows from this finite corpus. Privileged local SQL administration is
outside the HTTP adversary model.

No vulnerability-detection recall, false-positive rate or three-configuration enforcement rate is
claimed. These are functional/authorization regression tests, not the planned BOLA experiment.
No deliberate flaws, public deployment, external-target testing, ownership transfer, unrelated
features or final academic report/slides/recording were created. Stop here and obtain approval for M3.
