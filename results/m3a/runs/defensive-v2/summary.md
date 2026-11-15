# M3-A defensive API evaluation

Source commit: `7bdccc94155341a6403f8e1690f260683ec75071`.
Inventory SHA-256: `9012cfba09f1e15d97558d7041a1afbe18c025f689c9ddf37382a9e77d38ed21`.

Only endpoint-specific authorization was evaluated. No seeded-defect recall or three-configuration comparison is claimed.

Run complete: **True**. Run passed: **True**.

Planned: 56; responses received: 56; passed: 56; failed: 0; inconclusive: 0.

| Measure | Numerator | Denominator | Value | Complete |
|---|---:|---:|---:|---|
| authorization_enforcement_accuracy | 47 | 47 | 100.00% | True |
| unauthorized_operation_success_rate | 0 | 29 | 0.00% | True |
| legitimate_operation_success_rate | 18 | 18 | 100.00% | True |
| detector_false_positive_rate | 0 | 18 | 0.00% | True |
| live_seeded_defect_recall | 0 | 0 | unavailable | not evaluated |

Rates describe eligible observations only. Consult metrics.json for excluded IDs and execution errors.
Detector calibration fixtures are unit tests, not live API evidence. An incorrect legitimate denial is not automatically a detector false positive.

| ID | Functional result | Enforcement | Detector |
|---|---|---|---|
| H1 | passed | not_applicable | not_applicable |
| H2 | passed | not_applicable | not_applicable |
| H3 | passed | not_applicable | not_applicable |
| H4 | passed | not_applicable | not_applicable |
| H5 | passed | not_applicable | not_applicable |
| H6 | passed | not_applicable | not_applicable |
| C1 | passed | compliant | no_finding |
| C2 | passed | compliant | no_finding |
| C3 | passed | compliant | no_finding |
| C4 | passed | compliant | no_finding |
| C5 | passed | compliant | no_finding |
| C6 | passed | compliant | no_finding |
| A1 | passed | compliant | no_finding |
| A2 | passed | compliant | no_finding |
| A3 | passed | compliant | no_finding |
| A4 | passed | compliant | no_finding |
| A5 | passed | compliant | no_finding |
| A6 | passed | compliant | no_finding |
| N1 | passed | compliant | no_finding |
| N2 | passed | compliant | no_finding |
| N3 | passed | compliant | no_finding |
| N4 | passed | compliant | no_finding |
| N5 | passed | compliant | no_finding |
| N6 | passed | compliant | no_finding |
| X1 | passed | compliant | no_finding |
| X2 | passed | compliant | no_finding |
| X3 | passed | compliant | no_finding |
| X4 | passed | compliant | no_finding |
| X5 | passed | compliant | no_finding |
| X6 | passed | compliant | no_finding |
| L1 | passed | compliant | no_finding |
| L2 | passed | compliant | no_finding |
| L3 | passed | compliant | no_finding |
| L4 | passed | compliant | no_finding |
| L5 | passed | compliant | no_finding |
| L6 | passed | compliant | no_finding |
| I1 | passed | compliant | no_finding |
| I2 | passed | compliant | no_finding |
| I3 | passed | compliant | no_finding |
| I4 | passed | compliant | no_finding |
| I5 | passed | not_applicable | not_applicable |
| I6 | passed | not_applicable | not_applicable |
| R1 | passed | compliant | no_finding |
| R2 | passed | compliant | no_finding |
| R3 | passed | compliant | no_finding |
| R4 | passed | compliant | no_finding |
| R5 | passed | compliant | no_finding |
| R6 | passed | compliant | no_finding |
| E1 | passed | compliant | no_finding |
| E2 | passed | compliant | no_finding |
| E3 | passed | compliant | no_finding |
| E4 | passed | compliant | no_finding |
| E5 | passed | compliant | no_finding |
| E6 | passed | not_applicable | not_applicable |
| E7 | passed | compliant | no_finding |
| E8 | passed | compliant | no_finding |
