# Planned defect-class mapping — no defects installed in M3-A

| Class | Attack mechanism if such a flaw existed | Frozen relevant scenarios |
|---|---|---|
| B01 | Obtain another project's task by substituting its identifier | N2, X3, I2, R5, E8 |
| B02 | Receive task records outside permitted list scope | L3, L4, L5 |
| B03 | Modify a task without current write permission | A2, N4, X5, I3, R4, R6 |
| B04 | Delete a task without owner permission | A3, A4, N5, X6, I4 |
| B05 | Create a task in a project without current creation permission | A1, N3, X4 |

These are planned classes, not evidence that the defensive API contains them. Mapping is also
machine-readable in the frozen inventory. One class may have multiple probes; repeated findings
never become multiple distinct seeded vulnerabilities. A generic scope violation without a
matching mapped class is not automatically credited to a planned defect.

Calibration tests construct labelled observation data for all five classes and compliant controls.
They do not create vulnerable routes or modify application authorization. Live recall remains null
until a separately authorized, independently labelled defective configuration is actually evaluated.
