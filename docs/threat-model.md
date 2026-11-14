# Threat model and safety boundaries

The research adversary is an authenticated synthetic user controlling paths/bodies and knowing
other fixture IDs. Assets: task/project confidentiality, membership integrity and authorized state
changes. The attacker cannot change deployment settings or access database credentials.

| Threat | Defense/status |
|---|---|
| Stolen/forged or expired identity | M1 Argon2id, random tokens, digest lookup, expiry/revocation |
| Same-org or cross-org object access | M2 explicit endpoint membership/action checks; central scoped access deferred |
| Parent/child mismatch | Composite FKs and explicit complete-path endpoint checks |
| List disclosure | M2 endpoint-local SQL filters with exact-content assertions |
| Membership revocation | M2 current membership checks rather than token role claims |
| Accidental vulnerable startup | Hardened default, opt-in gates; baseline always rejected in M2 |
| Accidental exposure | Literal loopback API mapping, no DB host port, internal network |
| Credential response leakage | Strict output schemas, redacted validation, no-store, no access logs |
| Destructive test reset | Explicit local `_test` database; no fallback to application DB |

The container API listens on a wildcard interface for Docker networking; host publishing is literal
loopback. Settings cannot detect arbitrary operator-created port overrides, proxies or tunnels.
Future baseline activation needs renewed verification. A private repository is not network isolation.

Compose credentials and fixture passwords are public synthetic lab values. The lab DB account has
administration privileges; a hosted hardened demonstration would need separate least-privilege roles,
TLS, brute-force controls and deployment review. Identity verification/recovery are not implemented.
Duplicate registration reveals a synthetic account's existence. Dummy password verification reduces
obvious unknown-user timing differences but does not establish constant-time login or DoS resistance.

No real credentials/data, external targets, university systems, password attacks, injection research,
file uploads or general scanning. Parameterized-query regression checks do not expand research scope.
Public release review must check secrets, observations/screenshots, configuration and lab warnings.
