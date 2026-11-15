# Frozen M3-A scenario inventory

Version m3a-1. Literal expectations are in `src/bola_lab/evaluation/inventory.json`.
Changing outcomes requires an explicit versioned research amendment, never an observed-result rewrite.

| ID | Scenario | Actor | Category | Permission | Status | Defect classes |
|---|---|---:|---|---|---:|---|
| H1 | Valid login | 1 | authentication | allow | 200 | — |
| H2 | Wrong password | 1 | authentication | deny | 401 | — |
| H3 | Missing token | 1 | authentication | deny | 401 | — |
| H4 | Malformed token | 1 | authentication | deny | 401 | — |
| H5 | Expired token | 1 | authentication | deny | 401 | — |
| H6 | Revoked token | 1 | authentication | deny | 401 | — |
| C1 | Owner reads task | 1 | authorization | allow | 200 | — |
| C2 | Editor creates task | 2 | authorization | allow | 201 | — |
| C3 | Editor updates owner-created task | 2 | authorization | allow | 200 | — |
| C4 | Viewer reads task | 3 | authorization | allow | 200 | — |
| C5 | Owner deletes task | 1 | authorization | allow | 204 | — |
| C6 | Organization member creates owned project | 4 | authorization | allow | 201 | — |
| A1 | Viewer creates task | 3 | authorization | deny | 403 | B05 |
| A2 | Viewer updates task | 3 | authorization | deny | 403 | B03 |
| A3 | Viewer deletes task | 3 | authorization | deny | 403 | B04 |
| A4 | Editor deletes task | 2 | authorization | deny | 403 | B04 |
| A5 | Editor updates project | 2 | authorization | deny | 403 | — |
| A6 | Editor adds membership | 2 | authorization | deny | 403 | — |
| N1 | Read project | 4 | authorization | deny | 404 | — |
| N2 | Read task | 4 | authorization | deny | 404 | B01 |
| N3 | Create task | 4 | authorization | deny | 404 | B05 |
| N4 | Update task | 4 | authorization | deny | 404 | B03 |
| N5 | Delete task | 4 | authorization | deny | 404 | B04 |
| N6 | List memberships | 4 | authorization | deny | 404 | — |
| X1 | Read organization | 5 | authorization | deny | 404 | — |
| X2 | Read project | 5 | authorization | deny | 404 | — |
| X3 | Read task | 5 | authorization | deny | 404 | B01 |
| X4 | Create task | 5 | authorization | deny | 404 | B05 |
| X5 | Update task | 5 | authorization | deny | 404 | B03 |
| X6 | Delete task | 5 | authorization | deny | 404 | B04 |
| L1 | Exact organization list | 1 | authorization | allow | 200 | — |
| L2 | Exact project list | 1 | authorization | allow | 200 | — |
| L3 | Exact task list | 1 | authorization | allow | 200 | B02 |
| L4 | Nonmember task list | 4 | authorization | deny | 404 | B02 |
| L5 | Cross-organization task list | 5 | authorization | deny | 404 | B02 |
| L6 | Authorized empty project list | 1 | authorization | allow | 200 | — |
| I1 | Wrong org/project with caller in both organizations | 1 | authorization | deny | 404 | — |
| I2 | Mismatched task read | 1 | authorization | deny | 404 | B01 |
| I3 | Mismatched task update | 1 | authorization | deny | 404 | B03 |
| I4 | Mismatched task delete | 1 | authorization | deny | 404 | B04 |
| I5 | Reject body project_id reassignment | 1 | validation | deny | 422 | — |
| I6 | Reject body organization_id reassignment | 1 | validation | deny | 422 | — |
| R1 | Owner adds editor | 1 | authorization | allow | 201 | — |
| R2 | Owner downgrades editor | 1 | authorization | allow | 200 | — |
| R3 | Owner removal rejected | 1 | authorization | deny | 409 | — |
| R4 | Downgraded member loses writes with same token | 2 | authorization | deny | 403 | B03 |
| R5 | Removed member loses reads with same token | 6 | authorization | deny | 404 | B01 |
| R6 | Removed member loses writes with same token | 6 | authorization | deny | 404 | B03 |
| E1 | Owner creates task | 1 | authorization | allow | 201 | — |
| E2 | Owner updates task | 1 | authorization | allow | 200 | — |
| E3 | Owner updates project | 1 | authorization | allow | 200 | — |
| E4 | Owner deletes project and its children | 1 | authorization | allow | 204 | — |
| E5 | Owner lists exact memberships | 1 | authorization | allow | 200 | — |
| E6 | Second owner assignment rejected | 1 | validation | deny | 422 | — |
| E7 | Promoted viewer creates task with same token | 3 | authorization | allow | 201 | — |
| E8 | Other-project owner cannot read task | 7 | authorization | deny | 404 | B01 |
