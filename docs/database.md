# Database design and M2 transaction boundaries

`migrations/001_foundation.sql` remains unchanged from M1. Its schema supports all approved M2
resources; no migration was added merely to rename a milestone. See the ER diagram in architecture.md.

| Relation | Keys and invariants |
|---|---|
| users | Identity bigint PK; unique normalized email; Argon2id hash |
| organizations | Identity PK; name; creator FK; timestamp |
| organization_memberships | Composite `(organization_id,user_id)` PK; both parents must exist |
| projects | Identity PK; organization FK; unique `(organization_id,id)`; creator FK |
| project_memberships | `(project_id,user_id)` PK; checked role; composite project/tenant and organization-member FKs |
| tasks | Identity PK; composite project/tenant FK; content, checked status, creator and timestamps |
| auth_sessions | Token digest PK; user FK; expiry/revocation; no plaintext tokens or roles |
| schema_migrations | Applied SQL name, SHA-256 digest, application timestamp |

Exactly-one ownership is stronger than a unique index alone. The partial unique index forbids two
owner rows. Deferred constraint triggers check at transaction commit that every surviving project
has an owner. Immediate triggers prohibit removing/reassigning its owner while the parent exists.
Project and owner creation commit together; project deletion legitimately cascades to child rows.
These are ordinary-DML integrity guarantees; privileged administrative TRUNCATE/DDL can bypass
triggers, which is why the lab administration account is outside the HTTP adversary model.

M2 endpoint mutations lock the project row in one statement, then read membership and parent context
in a subsequent statement using PostgreSQL READ COMMITTED isolation. The separate read obtains a
fresh snapshot after any lock wait. API membership changes and task/project writes use the same
project lock, keeping their authorization and mutation within one transaction. Reads consult current
membership without a cache. Requests starting after a committed revocation are denied. Broad
concurrent/load behavior has not been exhaustively tested and must not be inferred from sequential cases.

Repository functions perform reusable data/business operations but grant no authorization.
Each endpoint checks organization membership, actual parent IDs, project role and (where applicable)
task relationship explicitly before mutation. This is intentionally distinct from the later
centralized authorization implementation with tenant-scoped repository access.

Psycopg parameters carry caller data. Statement, lock and connection timeouts remain enabled.
Injected failures after organization/project/task inserts verify rollback of all domain rows;
sequence values may advance on rollback, as expected in PostgreSQL. Synthetic reset restores them.
No production role separation, RLS, transfer workflow or public organization-admin API is introduced.
