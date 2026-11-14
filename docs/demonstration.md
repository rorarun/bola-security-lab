# M1 authentication demonstration

## M2 role-based collaboration (current milestone)

Start the current API and load the synthetic seed as in the README, then run:

```sh
docker compose exec -T api python - < scripts/demo_collaboration.py
```

The script performs real local HTTP calls for owner-created project, owner-managed editor/viewer
memberships, editor-created/updated task, viewer read, denied viewer update and editor delete,
denied outsiders, a verified parent mismatch, exact task listing, revocation with the same session,
and owner deletion. It deletes its temporary project and revokes its sessions afterward. Prerequisite:
unmodified fixture users and task 1 under project 1. It never resets unrelated data.
Its JSON output records methods, resource paths, synthetic bodies, statuses and responses; credentials
and bearer headers are omitted. Capture that output for the academic report. Only label it verified
after a successful run; actual M2 output is in `results/m2/demo.json`.

The remaining authentication instructions also remain useful, but statements below about deferred
BOLA demonstrations refer to deliberate exploit demonstrations, which are still outside M2.

Prerequisite: API ready and synthetic seed loaded using README commands. These commands exercise
authentication only. BOLA demonstrations are deferred until explicit approval for later milestones.
Never record bearer tokens or passwords in screenshots of real accounts.

Verified, portable container-side HTTP demonstration (requires no host-published port):

```sh
docker compose exec -T api python - < scripts/demo_auth.py
```

This performs real HTTP readiness, login, identity, logout and revoked-token requests, asserts
their responses and prints only sanitized results. It does not use ASGI's in-process test transport.
Capture the output for the M1 demonstration. The script has a fixed local URL, not an external target.

The equivalent host-side curl flow below is provided for ordinary local Docker installations. It
could not be verified from the managed cloud command shell: its request to the configured published
loopback port was refused while container-side requests succeeded. Do not broaden the published
address to work around that environment limitation. Requires curl and Python 3.

```sh
curl --fail --silent http://127.0.0.1:8000/health/ready

lab_token=$(curl --fail --silent http://127.0.0.1:8000/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@alpha.example","password":"Synthetic-Lab-Only-2026!"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl --fail --silent http://127.0.0.1:8000/users/me \
  -H "Authorization: Bearer $lab_token"

curl --silent -o /dev/null -w '%{http_code}\n' -X DELETE \
  http://127.0.0.1:8000/auth/token -H "Authorization: Bearer $lab_token"

curl --silent -o /dev/null -w '%{http_code}\n' \
  http://127.0.0.1:8000/users/me -H "Authorization: Bearer $lab_token"
unset lab_token
```

Expected: ready status; identity `{"id":1,"email":"owner@alpha.example"}`; logout `204`; reused token
`401`. Capture only resulting identity/status lines, not expanded commands containing tokens.
Interactive OpenAPI at `/docs` describes the implemented routes. JSON credentials are used for login;
this is an opaque bearer scheme, not an OAuth2 authorization server.

Foundation tests additionally exercise registration, invalid/expired/revoked sessions, digest/hash
storage and database constraints. Future demos must show authorized sharing, local ID substitution,
denied writes, database state and membership revocation using the same scenario inventory.
