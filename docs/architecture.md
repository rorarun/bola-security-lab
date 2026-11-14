# Architecture and schema

M1 uses synchronous FastAPI handlers, strict Pydantic credentials, opaque sessions, Psycopg transaction
contexts, SQL migrations and a seed CLI. Connections have connection/statement/lock timeouts.
Writes commit before handlers return. There is no ORM or extra migration framework.

```mermaid
flowchart TD
    C[HTTPX tests / local client] --> F[FastAPI + Pydantic]
    F --> A[Argon2id and session authentication]
    A --> Q[Psycopg transactions]
    Q --> D[(PostgreSQL)]
    M[Checksummed SQL migration CLI] --> D
    S[Explicit synthetic seed CLI] --> D
    F -. future resource API .-> P{Startup-selected authorization}
    P -.-> B[Baseline selected omissions]
    P -.-> E[Endpoint-specific checks]
    P -.-> H[Central policy + tenant-scoped queries]
    B -.-> Q
    E -.-> Q
    H -.-> Q
```

```mermaid
erDiagram
    USERS ||--o{ ORGANIZATION_MEMBERSHIPS : joins
    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERSHIPS : contains
    ORGANIZATIONS ||--o{ PROJECTS : contains
    PROJECTS ||--|{ PROJECT_MEMBERSHIPS : has
    ORGANIZATION_MEMBERSHIPS ||--o{ PROJECT_MEMBERSHIPS : qualifies
    PROJECTS ||--o{ TASKS : owns
    USERS ||--o{ AUTH_SESSIONS : authenticates
    USERS ||--o{ TASKS : creates
    USERS {
        bigint id PK
        varchar email UK
        text password_hash
    }
    PROJECTS {
        bigint id PK
        bigint organization_id FK
        bigint created_by FK
    }
    PROJECT_MEMBERSHIPS {
        bigint project_id PK,FK
        bigint user_id PK,FK
        bigint organization_id FK
        text role
    }
    TASKS {
        bigint id PK
        bigint organization_id FK
        bigint project_id FK
        text status
    }
    AUTH_SESSIONS {
        char token_digest PK
        bigint user_id FK
        timestamptz expires_at
        timestamptz revoked_at
    }
```

Composite foreign keys enforce matching tenant/project IDs and same-organization project members.
Integer IDs make substitution experiments clear; they are not secrets. A partial unique owner index
prevents two owners; a deferred constraint prevents zero at commit. Owner mutation/removal triggers
also prohibit transfer. Deleting a project removes its memberships/tasks.

Migration application is transactional and uses an advisory lock. `schema_migrations` records names,
SHA-256 digests and application timestamps. Changed/missing applied files are rejected. Startup checks
the exact history. Add migrations rather than editing applied ones; no destructive downgrade exists.

Argon2id uses 19 MiB memory, two iterations, one lane and independent salts. Tokens have 256 random
bits and a maximum 15-minute lifetime. Only SHA-256 token digests are stored, with expiry/revocation.
Fast hashing is suitable for high-entropy tokens, not human passwords. No roles are stored in tokens.

Fixture equivalence fixes IDs, content and timestamps; password salts and issued tokens correctly
remain random. Authentication establishes identity; future membership policies establish permissions.
