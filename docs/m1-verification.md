# M1 foundation verification

Historical snapshot: reproduce from `feature/m1-foundation` at
`7047806e2e60e33efa8222eb6aeb6ffdc8f3be99`. The current M2 checkout intentionally differs from
the M1 source hashes. M1 evidence is preserved; current verification writes to `results/m2/`.
M1 was revalidated with 58 passing tests before preservation and its push-triggered CI succeeded.

This records local verification only. No task authorization implementation or BOLA experiment has
been executed. `results/m1/junit.xml` and `results/m1/manifest.json` preserve actual test cases,
counts, source checksums, image IDs, PostgreSQL version and environment limitations.

## Executed checks

- Dependency resolution and installation from exact runtime/development lockfiles succeeded.
- Ruff lint and formatting checks passed. Rendered Compose configuration validated.
- Runtime and test image builds succeeded with a temporary BuildKit CA-secret adaptation.
- PostgreSQL started, checksummed migrations applied, and API startup/readiness passed.
- Full suite: **58 passed, 0 failed, 0 errors, 0 skipped** on real PostgreSQL.
- Synthetic seed loaded. Repeatability/reset and identity sequences verified in integration tests.
- Live HTTP demonstration via `scripts/demo_auth.py`: readiness, login, correct identity,
  logout `204`, rejected revoked token `401`. It prints no tokens.
- Docker inspection recorded an API host binding of `127.0.0.1:8000` and no DB host binding.
  API runs as `10001:10001`, with a read-only root filesystem.
- Startup rejection tests cover unsafe mode/environment/opt-in settings, loopback requirements,
  invalid TTLs, unsupported settings, and M1's rejection of all experimental configurations.

The foundation suite checks authentication responses and actual password/token database storage;
expiry/revocation; validation secrecy; migration repeatability/tampering/rollback; deterministic
fixtures; tenant relationship constraints; exactly-one-owner behavior; and deletion cascades.
The number of foundation tests is not a claim to meet the later >=40 security-scenario requirement.

## Failures encountered and resolved

1. uv could not write its default home cache. Using `/tmp/bola-uv-cache` resolved installation.
2. Normal Docker pip downloads failed certificate verification behind the cloud proxy. A temporary
   Dockerfile mounted the environment's CA bundle as a secret; TLS verification stayed enabled.
3. Initial container startup/tests could not read copied source files with restrictive workspace
   permissions. The Dockerfile now grants read/directory traversal permissions before using the
   non-root runtime user. The full suite and startup passed after correction.
4. The first lint pass found formatting/line-length issues; source was formatted and checks passed.

An initial test invocation also used an unsupported `compose run --no-build` flag; that command
did not execute tests. The successful invocation below uses the already-built test image.

## Remaining environment limits and risks

The managed command shell refused host-loopback HTTP connections even though the API was healthy
inside Docker and the configured binding was correct. The ordinary host curl demo is therefore
unverified here; the documented container-side real-HTTP demonstration passed. Do not broaden host
publishing as a workaround. Normal local Docker build/setup still needs confirmation outside this
cloud certificate/network environment.

Starlette emitted one deprecation warning about its HTTPX-backed TestClient. Tests retain HTTPX as
required; the warning was not suppressed. GitHub-hosted Actions has not run this uncommitted work.
No repository push, deployment, external-target testing, load/concurrency testing or production
security review was performed. Lab credentials and an administrative DB role are unsuitable for
public hosting. See the threat model for limitations and prerequisites for any future hardened host.

## Reproduce and preserve the suite

After building images and creating the disposable test database as in the README:

```sh
python3 scripts/verify_foundation.py
python3 scripts/record_foundation.py results/m1/junit.xml results/m1/manifest.json
```

The verifier streams JUnit out before the read-only test container's temporary filesystem is removed.
An initial attempt to copy JUnit after exit failed because `/tmp` is ephemeral; that run passed but
did not preserve its XML. The streaming verifier reruns the suite and preserves its actual output.
The manifest records a dirty worktree/source hashes when changes are not
committed; it does not misidentify the initial commit as the implemented source revision.

M1 is the stopping point. M2 needs explicit user approval after reviewing these results.
