# Research inventory amendments

## m3a-1 → m3a-2: E5 membership list order

Initial inventory commit: `2b55d1b`. Its live run is preserved unchanged in
`results/m3a/runs/initial-v1/`, including its original inventory/checksum and all observations.
The run executed 56 scenarios: 55 passed and E5 failed its response contract. No execution errors
or inconclusive scenarios occurred. Enforcement evaluation remained compliant for E5.

The initial artifact accidentally ordered E5's expected memberships by role through the fixture's
canonical JSON ordering: user IDs `[2, 1, 3]`. The pre-existing M2 contract in `docs/api.md` explicitly
states that membership lists are ordered by user ID. The response correctly returned `[1, 2, 3]`.

Version m3a-2 changes only that expected array order and the inventory version/checksum. The member
IDs, roles, status, permissions, fields and persisted-state requirement remain identical. No API
code, authorization behavior, expected denial, detector threshold or assertion is weakened. This
is a documented correction to the independent oracle against the already approved API contract,
not evidence that the first run passed. Later runs use a new evidence directory and checksum.
