# BOLA Security Lab — Research Evidence

This directory contains the verification artifacts and experimental results for **Detecting and Preventing Broken Object-Level Authorization in a Collaborative Task Management API**, developed for COMP 3123 — Computer Security at Acadia University.

The final controlled comparative experiment was completed on **November 16, 2026**.

## 1. Final M5 Comparative Study

**Evidence directory:** [`m5-comparison-20261116/`](m5-comparison-20261116/)

The experiment evaluated three implementations of the collaborative task-management API:

1. **Vulnerable baseline:** A deliberately flawed implementation containing five known BOLA defects.
2. **Endpoint-specific authorization:** Each protected endpoint independently enforces resource and action permissions.
3. **Centralized authorization:** Shared policy enforcement and scoped database operations protect resources.

Each implementation was evaluated against an identical authorization policy using synthetic data.

### Experiment Execution

| Measurement | Value |
|---|---:|
| Experimental treatments | 3 |
| Core scenarios per treatment | 56 |
| Supplemental scenarios per treatment | 6 |
| Total observations | 186 |
| Seeded baseline defect classes | 5 |
| Execution errors reported | 0 |

All 186 planned observations were completed.

## 2. Core Experimental Results

The following metrics refer to the **56 core scenarios per treatment**. Supplemental scenarios are reported separately.

| Metric | Vulnerable Baseline | Endpoint-Specific | Centralized |
|---|---:|---:|---:|
| Authorization enforcement accuracy | 24/47 (51.1%) | 47/47 (100%) | 47/47 (100%) |
| Unauthorized operation success | 21/29 (72.4%) | 0/29 (0%) | 0/29 (0%) |
| Legitimate operation success | 16/18 (88.9%) | 18/18 (100%) | 18/18 (100%) |
| Detector false positives on selected controls | 0/16 | 0/16 | 0/16 |
| Verified seeded-defect detection recall | 5/5 (100%) | N/A | N/A |

### Interpretation

The vulnerable baseline permitted 21 of 29 prohibited core operations, confirming that the deliberately introduced BOLA defects had observable security consequences.

Both defensive implementations prevented every tested prohibited core operation while preserving all 18 legitimate core operations.

The detector identified all five independently verified seeded defects in the baseline.

The endpoint-specific and centralized implementations achieved identical measured defensive results. The experiment therefore **does not demonstrate that centralized authorization is more secure than correctly implemented endpoint-specific authorization**.

These findings are limited to the controlled scenarios and do not establish general vulnerability-scanning accuracy or production security guarantees.

## 3. Supplemental Evaluation

Six additional scenarios were executed for each treatment.

| Measurement | Baseline | Endpoint | Centralized |
|---|---:|---:|---:|
| Scenarios satisfying expected outcomes | 4/6 | 6/6 | 6/6 |
| Unauthorized operation success | 1/2 | 0/2 | 0/2 |
| Legitimate operation success | 0/1 | 1/1 | 1/1 |

The supplemental scenarios have no eligible false-positive controls or known-present seeded defects. Their false-positive and recall metrics are therefore **not applicable**, rather than 0%.

## 4. Final Research Evidence Files

The [`m5-comparison-20261116/`](m5-comparison-20261116/) directory contains:

| File or Directory | Description |
|---|---|
| `comparison.md` | Human-readable summary of the three-treatment comparison |
| `comparison.json` | Detailed machine-readable results and numerical metrics |
| `manifest.json` | Experiment provenance, source hashes, database version, and timestamps |
| `baseline/` | Vulnerable baseline results, observations, labels, and evaluation outputs |
| `endpoint/` | Endpoint-specific authorization results |
| `centralized/` | Centralized authorization results |
| `inventory.json` | Frozen security scenario inventory |
| `fixture.json` | Synthetic test fixtures |
| `registry.json` | Seeded-defect registry |
| `supplement.json` | Supplemental scenario definitions |
| `baseline-profile.json` | Baseline behavior profile |
| `confirmed-violations.png` | Visualization of confirmed security violations |
| `operation-outcomes.png` | Visualization of authorized and prohibited operation outcomes |
| `distinct-defect-detection.png` | Visualization of detected seeded defect classes |

Additional SHA-256 checksum files allow evidence integrity checks.

## 5. Source Provenance

The original experiment was performed using evaluator version `study-1` and PostgreSQL 17.7.

The manifest records:

- Experiment start and completion timestamps.
- PostgreSQL database and server version.
- Source-file SHA-256 hashes.
- Frozen fixture and scenario hashes.
- Observation hashes.
- Execution error records.

The original manifest identifies source commit `5369ac9` and records that the working tree contained uncommitted changes during execution.

The evaluated implementation was subsequently preserved in commit `583a542`, and the experimental evidence was committed as `4a28acf`.

The original manifest is retained unchanged to preserve the historical record of the experiment.

A clean-checkout rerun would provide stronger independent reproducibility evidence. The preserved run should not be described as having been executed from a clean Git working tree.

## 6. Earlier Milestones

Earlier verification artifacts are retained to document the development and testing history.

### M1 — Authentication and Database Foundation

Directory: [`m1/`](m1/)

Includes evidence related to authentication, database setup, migrations, and synthetic user fixtures.

### M2 — Collaborative Task Management API

Directory: [`m2/`](m2/)

Includes API functionality and authorization verification for project roles, task operations, and membership management.

### M3-A — Initial Authorization Evaluation Framework

Directory: [`m3a/`](m3a/)

Includes the original defensive evaluation framework, its frozen scenario inventory, and historical results.

The initial run exposed an evaluation-oracle ordering error. Its failed evidence was retained, and a subsequent corrected run completed 56/56 scenarios.

The M3-A results represent an earlier milestone and should not be confused with the final M5 three-treatment comparison.

## 7. Reproduction and Validation

The study's source code and scripts are included in the repository.

Relevant files include:

- `scripts/run_evaluation.py`
- `src/bola_lab/evaluation/study.py`
- `src/bola_lab/evaluation/runner.py`
- `src/bola_lab/evaluation/reports.py`
- `docs/evaluation/reproduction.md`

The complete three-treatment study is selected through the evaluation runner's `--study` option.

Reproduction requires Python development dependencies, Docker, a dedicated disposable PostgreSQL evaluation database, and an explicitly configured `BOLA_EVALUATION_DATABASE_URL`.

Every new evaluation must use a separate output directory. Existing evidence must not be overwritten.

The current GitHub Actions workflow verifies automated tests and the earlier evaluation framework; it does not automatically rerun the complete M5 comparative study.

## 8. Research Limitations

- The study uses synthetic identities and task-management data.
- The baseline defects were deliberately introduced.
- Security measurements cover a finite, predetermined set of scenarios.
- The detector was evaluated against five known-present seeded defect classes.
- False-positive results apply only to selected negative controls.
- The study did not establish a general performance or maintainability advantage for centralized authorization.
- The implementation and evaluation framework were developed within the same project, limiting independent validation.
- Results do not guarantee security against unknown attacks or production threats.

The vulnerable baseline is intended strictly for isolated, authorized academic research. It must not be publicly deployed.

---

**Final study status:** Completed controlled comparison with preserved experimental evidence. Historical milestone artifacts remain available for review.
