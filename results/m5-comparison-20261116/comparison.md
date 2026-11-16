# Executed security treatment comparison

Source: `5369ac946df69a1213b7c2dd18c371e05e205f3f`; evaluator: `study-1`.
Normative policy is identical across treatments. Expected seeded violations remain policy failures even when experimental verification passes.

| Treatment | Enforcement | Prohibited success | Legitimate success | Detector FP | Live seeded recall |
|---|---|---|---|---|---|
| baseline | 24/47 | 21/29 | 16/18 | 0/16 | 5/5 |
| endpoint | 47/47 | 0/29 | 18/18 | 0/16 | not applicable |
| centralized | 47/47 | 0/29 | 18/18 | 0/16 | not applicable |

Core metrics use only the frozen 56-case core; supplement metrics are separate in comparison.json.
False-positive controls are the same preregistered compliant controls for each treatment. Calibration examples are excluded.
No causal superiority of centralized over correct endpoint authorization is inferred from equal defensive outcomes.
