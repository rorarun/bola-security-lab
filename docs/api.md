# M2 API contract

Authentication uses `Authorization: Bearer <opaque-token>`. `/auth/token` accepts JSON credentials,
not OAuth2 form data. Tokens, password hashes and internal authorization context never appear in
resource responses. `/docs` and `/openapi.json` provide generated schemas for all implemented routes.

Base resource path `P = /organizations/{org_id}/projects/{project_id}`.

| Method | Path | Body / behavior |
|---|---|---|
| POST | `/auth/register` | `{email,password}` -> public user, 201 |
| POST | `/auth/token` | `{email,password}` -> bearer token, type, expires_in |
| DELETE | `/auth/token` | Revoke current session, 204 |
| GET | `/users/me` | Authenticated user's ID/email |
| GET | `/health/live`, `/health/ready` | Liveness/database readiness |
| POST | `/organizations` | `{name}` -> organization + creator membership atomically, 201 |
| GET | `/organizations` | Exactly caller's organizations |
| GET | `/organizations/{org_id}` | Current organization membership required |
| POST | `/organizations/{org_id}/projects` | `{name,description?}` -> project + sole owner atomically, 201 |
| GET | `/organizations/{org_id}/projects` | Organization membership required; only joined projects |
| GET | `P` | Current project member reads project |
| PATCH | `P` | Owner updates `{name?,description?}` |
| DELETE | `P` | Owner deletes project/tasks/memberships atomically, 204 |
| GET | `P/memberships` | Owner lists this project's memberships |
| POST | `P/memberships` | Owner adds `{user_id,role}`; target must already belong to organization, 201 |
| PATCH | `P/memberships/{user_id}` | Owner changes `{role}` of non-owner |
| DELETE | `P/memberships/{user_id}` | Owner revokes non-owner, 204 |
| POST | `P/tasks` | Owner/editor creates `{title,description?,status?}`, 201 |
| GET | `P/tasks` | Members list exactly this project's tasks |
| GET | `P/tasks/{task_id}` | Members read a task matching the complete parent path |
| PATCH | `P/tasks/{task_id}` | Owner/editor updates `{title?,description?,status?}` |
| DELETE | `P/tasks/{task_id}` | Owner deletes matching task, 204 |

Organization membership provisioning has **no HTTP endpoint**. Explicit local lab operator command:

```sh
docker compose run --rm -e BOLA_LAB_OPT_IN=true migrate \
  bola-lab organization-member --organization-id 2 --user-id 4
```

Use existing registered synthetic IDs. This command refuses non-lab environments, absent opt-in,
nonpositive/oversized IDs, duplicates and missing parents. It does not grant project membership.
In fixture version 1 this deliberately adds synthetic Alpha outsider 4 to Beta organization 2.
It still grants no access to Beta project 3. Repeat execution reports a duplicate. Only a controlled
local operator can make this grant; there is no public organization-join endpoint.

Names: 1–120 characters after trimming; task titles: 1–200 after trimming; descriptions: up to 4000.
Task status: `todo`, `in_progress`, `done`. Membership request role: `editor` or `viewer`; only project
creation assigns `owner`. PATCH requires at least one allowed field and rejects explicit nulls.
Unknown fields, ownership/tenant/creator reassignment and invalid bigint identifiers return 422.
All lists are ordered by resource ID (memberships by user ID), with no pagination for this small lab.

Response objects include IDs, content, creator and timestamps; project/task objects include their
organization and project relationships. Memberships expose only organization_id, project_id,
user_id and role. Creation derives tenant from validated path and creator from authenticated identity.

Error contract: 401 authentication; 404 absent/out-of-scope object or mismatched path; 403 readable
project but forbidden action; 409 duplicate membership or owner removal/demotion; 422 invalid input.
Authentication precedes resource access. For task mutations, parent scope and task relationship are
checked before the action role. Error bodies contain generic details, not foreign object contents.

All successful writes commit before response completion. The approved matrix remains authoritative.
The complete three-configuration experiment and measured detection metrics are not part of M2.
