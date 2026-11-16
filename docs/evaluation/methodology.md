# M3-A methodology and measurement contract

This milestone evaluates the existing endpoint-specific API only. The `hardened` default retains
its M2 meaning. No vulnerable baseline, centralized implementation, new authorization configuration
or public target is introduced. The question about three comparative treatments remains unanswered.

## Frozen independent expectations

Commit 2b55d1b freezes 56 scenario definitions and the synthetic fixture contract before evaluation.
The documented E5 ordering amendment produces m3a-2; the original 55/56 run remains preserved.
See amendments.md for the exact change and pre-existing API contract supporting it.
Canonical review artifacts are `src/bola_lab/evaluation/inventory.json` and `fixture.json`, each with
a SHA-256 sidecar. `scenarios.md` lists IDs, permissions, status codes and relevant defect classes.
Expected body contents and persisted effects are literal inventory data, not application policy
calls. The implementation verifies actual fixtures against this independent contract before each
scenario. Any outcome change requires an explicit research amendment, new version/checksum, rationale
and reviewed commit; updating expectations to make observed failures disappear is prohibited.

Scenario categories and metric eligibility are computed from inventory fields, never a hardcoded
47-case denominator. Six authentication cases and three validation cases are reported separately.
The other cases represent authorization decisions. Setup actions do not inflate scenario counts.
An empty list must be exactly empty; missing permitted records fail functional verification.

## Execution and isolation

The harness uses only `bola_lab_evaluation_test` on an allowed local host. It never defaults to
the application or M2 regression database. A session advisory lock prevents concurrent harness runs
sharing the evaluation DB. This is not a general scanner and accepts no arbitrary HTTP URL.

The runner starts and owns a Uvicorn child with the explicit evaluation DSN and existing application
factory. It binds an OS-allocated loopback socket, passes the listener to the child, and uses real
HTTPX TCP requests with redirects disabled. Requests never go through an ASGI mock transport.
The API is stopped on exit. Published ports, Compose networks and application settings are unchanged.
Only controlled synthetic data is reset, once per scenario; multi-step cases retain their own state.

All seven identities authenticate and prove their `/users/me` identity before scenario execution.
Membership changes are established through owner HTTP requests. Revocation first proves the same
session could access the task, then removes membership before the primary request. The dual-org
fixture proves a wrong parent cannot be explained away by organization nonmembership.
Snapshot queries run on fresh connections after HTTP completion to inspect committed state.

## Evidence and interpretation

Each observation records stable ID, actor, sanitized request, independently validated setup,
actual response, before/after public domain state, safe session counts/proofs, timestamps and errors.
Authentication request credentials and response tokens are represented by symbolic/safe facts.
Hashes, digests, passwords and bearer headers are excluded or redacted. Known issued secrets are
also removed from nested strings. Errors preserve stage/type, not potentially sensitive diagnostics.

Four outputs are separate: execution errors, exact functional contract checks, authorization
enforcement, and task BOLA detector classification. A denial with a committed forbidden update is
an unauthorized success. A 5xx response cannot prove enforcement; a confirmed forbidden effect
remains a violation even when accompanied by an error. Missing required evidence is inconclusive.
An allowed read returning the wrong title can fail functionally without being a BOLA finding.

## Metrics

All rates include numerator, denominator, planned eligibility, excluded IDs and completeness.

| Metric | Definition |
|---|---|
| Authorization enforcement accuracy | Correct permission decision and resource scope / evaluable authorization cases |
| Unauthorized-operation success | Confirmed prohibited disclosure/effect / evaluable prohibited cases |
| Legitimate-operation success | Correct response and committed effects for permitted operation / completed permitted cases |
| Detector false-positive rate | Findings on independently compliant predeclared permitted controls / valid compliant controls |
| Live seeded-defect recall | Distinct known-present labelled seeded defects detected / distinct known-present labelled seeded defects evaluated |

Errors are not eligible secure outcomes. A positively proven violation remains decisive even with
execution errors. Exclusions and errors make the run incomplete; subset rates must not be described
as complete results. Zero denominators yield null. Incorrect denials reduce legitimate success and
enforcement accuracy; they are not automatically false positives. Permitted requests that actually
leak or alter forbidden data invalidate negative-control status and remain visible as violations.

No labelled defective API exists in M3-A, so live recall is unavailable with denominator zero.
The planned inventory total is five, not five known-present/evaluated defects. Multiple findings
for one class are deduplicated. Detector calibration uses clearly labelled observation fixtures in
unit tests; these fixtures are never included as live HTTP evidence or empirical recall figures.
Not every security test is a task BOLA probe; authentication, validation and membership controls
retain their separate purpose.

## Limits and threats to validity

This finite, nonrandom synthetic corpus and known class inventory cannot establish general scanner
accuracy or absence of unknown defects. Detector rules and the independent contract checker share
some scope checks, so live false-positive results are not independent statistical validation.
Calibration demonstrates rule behavior only. Password salts, bearer tokens and operation timestamps
are correctly nondeterministic; fixture identities/content and report regeneration are deterministic.
The current study is sequential; no broad concurrency, timing, prevalence or production-security
claim follows. Privileged fixture SQL is outside the HTTP adversary model.
