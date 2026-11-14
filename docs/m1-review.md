# M1 preservation review before M2

The initial worktree had uncommitted M1 files and an empty staging area. All source/configuration,
tests, SQL and evidence were inspected before M2 functionality was written. No sensitive `.env`
files, private-key/API-token patterns, issued bearer tokens or private credentials were found in
the candidate files. Plaintext passwords are deliberately synthetic seed/test/Compose examples,
documented as local-only; blanket claims that no plaintext examples exist would be inaccurate.
Evidence files are small. The prior history contained only README and Python ignore rules.

Checksums matched the prior recorded M1 source. Re-execution produced 58 passed, zero failures,
errors or skips; lint/format checks passed. PostgreSQL tests verified ownerless commit rejection,
second-owner rejection, owner removal/demotion/transfer rejection and legitimate project cascade.
The unique partial index ensures at most one owner; deferred constraints require at least one.
Settings retain the hardened default and rejected experimental startup during M1.

Preserved branch: `feature/m1-foundation`.
Commit: `7047806e2e60e33efa8222eb6aeb6ffdc8f3be99`.
Push was verified by remote branch SHA. `main` remained at
`6f4e766206894aa30b8eee406429f1fa18a7ee72`; no merge was performed.

Push-triggered GitHub Actions run 43651119476 completed successfully:
https://github.com/rorarun/bola-security-lab/actions/runs/43651119476
The job reported successful dependency installation, lint, formatting, Compose validation, pytest
and artifact upload. The CLI's initial API lookup was forbidden; the connected GitHub fetch tool
successfully retrieved the actual run and job status. CI success is an observed result, not inferred
from local tests. The run checks M1, not subsequent M2 code.

M2 branches separately from this verified snapshot. Historical evidence is not overwritten.
