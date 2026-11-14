# Preregistered experiment plan — not executed in M1

Research question: how effectively do multi-identity tests detect seeded BOLA, and can centralized
authorization prevent prohibited access while preserving legitimate collaboration? Results apply
only to the tested corpus. This document defines expectations before experimental implementation.

## Controlled comparison

Preserve three distinct implementations: selected authentication-only baseline operations;
endpoint-specific checks; centralized policy enforcement with tenant/project-scoped database access.
Use identical HTTP functionality, authentication, validation, schema, fixture content and scenario IDs.
Select configuration at startup, never by request. Reset fixtures before independent scenarios;
multi-step revocation cases retain state only within that scenario. Both defensive implementations
must satisfy the same independent permission matrix. Do not assume centralization improves measured
security when both implementations are correct; assess maintenance benefits separately.

| Planned seeded flaw | Baseline omission | Expected demonstrating scenario IDs |
|---|---|---|
| B01 | Task detail lookup by task ID without object authorization | N2, X3, I2, R5 |
| B02 | Task list query omits project/caller scope | L3, L4, L5 |
| B03 | Task update omits membership/action checks | A2, N4, X5, I3, R4, R6 |
| B04 | Task delete omits owner/object checks | A3, A4, N5, X6, I4 |
| B05 | Task creation skips target-project membership/action check | A1, N3, X4 |

All five retain authentication and schema checks. Non-seeded operations retain intended protection.
These are planned omissions, not existing vulnerable code. Refine exact endpoint mappings before M3
and review them against this inventory. Baseline observations must match their preregistered outcomes;
unexpected behavior fails verification. Defensive policy violations always fail regression checks.

## Complete initial scenario inventory (48 distinct scenarios)

The first plan has eight groups of six. Each scenario runs in all three configurations (144 executions,
not 144 distinct scenarios). Foundation tests do not substitute for this security corpus.

| IDs | Six scenarios, in ID order |
|---|---|
| H1–H6 | Valid login; wrong password; missing token; malformed token; expired token; revoked token |
| C1–C6 | Owner reads task; editor creates task; editor updates another member's task; viewer reads task; owner deletes task; organization member creates project |
| A1–A6 | Viewer creates task; viewer updates task; viewer deletes task; editor deletes task; editor updates project; editor manages memberships |
| N1–N6 | Same-org nonmember reads project; reads task; creates task; updates task; deletes task; reads membership list |
| X1–X6 | Cross-org outsider reads organization; reads project; reads task; creates task; updates task; deletes task |
| L1–L6 | Filter organization list; filter project list; filter task list; nonmember task list; cross-org task list; authorized empty-project task list |
| I1–I6 | Wrong organization/project pair; wrong project/task pair on read; on update; on delete; body project reassignment; body tenant reassignment |
| R1–R6 | Owner adds editor; owner downgrades editor to viewer; owner-removal attempt; downgraded member loses writes; removed member loses reads; removed member loses writes |

Independent expected outcomes come from the approved matrix, not production policy helpers. Authorized
list controls use exact permitted IDs and fields, including legitimate empty results. Denied mutations
assert unchanged rows and no side effects. Allowed mutations assert precise committed effects. Wrong
parent/child cases check that the unrelated target remains unchanged. Authentication scenarios must
also remain protected in baseline mode. Add further cases when edge conditions justify them.

## Observation, execution, detector, and enforcement records

Keep separate fields for run/configuration/scenario/actor IDs, expected permission, expected baseline
flaw and manifestation, HTTP status, sanitized returned IDs/data, pre/post-state comparison,
execution status (`completed`, `error`, `incomplete`), detector verdict, and actual enforcement outcome.
Tokens/passwords never appear in records. A `403` with a committed forbidden update is an unauthorized
success. A scoped list returning `200` is legitimate. Request timeouts/crashes are execution errors,
not evidence of correct enforcement. Assertions and detector observations must remain independently
reviewable; do not manufacture labels from a detector's own verdict.

## Metrics and denominators

| Measure | Definition |
|---|---|
| Distinct seeded flaws evaluated | Unique inventory flaws with completed, decisive eligible probes |
| Distinct seeded flaws detected | Evaluated flaws with at least one confirmed detector finding |
| Detection recall | Detected / evaluated; include both raw counts and planned total of five |
| Detector false-positive rate | Independently labelled permitted controls incorrectly flagged as vulnerability / completed permitted controls |
| Unauthorized-operation success | Completed prohibited scenarios disclosing protected data or committing prohibited effects / completed prohibited scenarios |
| Legitimate-operation success | Completed permitted scenarios with exact expected response/effects / completed permitted scenarios |
| Defensive regression results | Counts and case IDs for policy/functional failures separately for endpoint and centralized modes |

Detector permitted controls must be labelled before execution and contain verified nonviolating
behavior. Labels cover response/state behavior, not just whether the initial request was permitted:
an authorized list request that leaks other tenants' data is a real finding, not a false positive.
An incorrectly denied authorized request reduces legitimate-operation success; it is not
automatically a detector false positive. Include all errors, incomplete/skipped cases, planned and
completed denominators and scenario-level failures alongside rates. An incomplete run must be marked
incomplete even if its completed-case rates look good. Zero denominators yield null, not zero percent.
Both permitted and prohibited subsets can have legitimate data-field requirements; status alone is
insufficient. Use explicit positive/negative detector calibration examples to expose a detector that
never reports findings. Do not claim general scanner accuracy from this small controlled corpus.

## Evidence to generate in later milestones

Per-run manifest: exact source revision/dirty status or source digest, dependency versions, PostgreSQL
version, configuration, fixture/scenario versions, timestamps, execution counts and completeness.
Preserve raw JSONL, pytest JUnit, metrics JSON/CSV, three-configuration comparison tables and figures
generated from those files. Store in `results/runs/<run-id>/`. Claims in the report must trace to raw
records. Demo commands and screenshot instructions must be exercised before being labelled verified.

Threats to validity: small synthetic corpus, known seeded flaws, detector/author overlap, non-random
scenario selection, common business/authentication code, fixture-reset errors, status-only inference,
incomplete executions, and no established concurrency/performance generalization. No claims about
real-world prevalence, unseen flaws, or security outside tested operations.
