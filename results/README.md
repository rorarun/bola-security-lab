# Evidence status

`m1/` is the preserved foundation snapshot from `feature/m1-foundation` (commit 7047806).
`m2/` holds current functional/authorization regression JUnit, execution status, manifest and sanitized
live-HTTP requests/responses. Hosted CI status is available in GitHub Actions for exact pushed commits.
These are not comparative BOLA
experiment results. M2's tests do not establish detection recall or general scanner accuracy.

M1 results are foundation verification, not BOLA experimental findings. No recall, false-positive,
unauthorized-success or legitimate-success measurements exist yet. Do not report zeros for unrun
experiments or count foundation cases toward the planned security corpus.

`m1/` contains actual JUnit, a sanitized live-HTTP demonstration result and a verification manifest
from this checkout. Later experiment
runs will use `runs/<run-id>/` with raw JSONL observations, run completeness/errors, independent labels,
metrics JSON/CSV, defensive regression details, generated figures and three-configuration comparisons.
See `docs/experiment-plan.md`. Never store bearer tokens, raw passwords or real personal information.
