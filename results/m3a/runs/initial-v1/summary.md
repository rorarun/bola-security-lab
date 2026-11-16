# M3-A defensive API evaluation

Source commit: `2b55d1bb7932adf1c688edaf77146e8d3c39f130`.
Inventory SHA-256: `10e25e73d6f11c831fa93105c96294fd36d1d158b35efd987b448bc95f53f326`.

Only endpoint-specific authorization was evaluated. No seeded-defect recall or three-configuration comparison is claimed.

Run complete: **True**. Run passed: **False**.

Planned: 56; responses received: 56; passed: 55; failed: 1; inconclusive: 0.

| Measure | Numerator | Denominator | Value | Complete |
|---|---:|---:|---:|---|
| authorization_enforcement_accuracy | 47 | 47 | 100.00% | True |
| unauthorized_operation_success_rate | 0 | 29 | 0.00% | True |
| legitimate_operation_success_rate | 17 | 18 | 94.44% | True |
| detector_false_positive_rate | 0 | 17 | 0.00% | False |
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
| E5 | failed | compliant | no_finding |
| E6 | passed | not_applicable | not_applicable |
| E7 | passed | compliant | no_finding |
| E8 | passed | compliant | no_finding |
