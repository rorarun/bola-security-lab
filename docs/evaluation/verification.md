# M3-A implementation verification

Evaluated code commit: `7bdccc94155341a6403f8e1690f260683ec75071`, with a clean working tree at
run start, on `feature/m3-evaluation-framework`. The subsequent evidence commit preserves these
outputs without changing that tested code. No merge to main is authorized.

## Executed outcomes

The definitive run is `results/m3a/runs/defensive-v2/`. All 56 primary HTTP requests returned
responses; 56 scenarios passed, zero failed, zero were inconclusive, and no setup/execution errors
occurred. PostgreSQL 17.7 and a harness-owned Uvicorn process were exercised through real HTTPX TCP
requests. The host wrapper confirmed that container source/test/migration bytes matched the checkout.
The API's authorization behavior, authentication, migrations and Compose bindings remain unchanged.

Eligibility was calculated from the frozen inventory: six authentication, 47 authorization and
three validation scenarios. The authorization set contains 18 permitted and 29 prohibited operations.

| Measure | Actual numerator/denominator | Value |
|---|---:|---:|
| Authorization enforcement accuracy | 47/47 | 100% |
| Unauthorized-operation success | 0/29 | 0% |
| Legitimate-operation success | 18/18 | 100% |
| Detector false positives on compliant permitted controls | 0/18 | 0% |
| Live seeded-defect recall | 0/0 evaluated | Unavailable |

There were no excluded authorization cases or invalidated permitted controls in this run. No live
task BOLA findings were observed. This is evidence about the tested scenarios, not a claim that no
unknown vulnerabilities exist. None of the five planned defect classes is installed/evaluated as a
known-positive API defect. Unit calibration findings are not included in the above live rates.

## Regression and failure-path verification

The PostgreSQL-backed pytest run passed all **241 tests**: the existing **207 M1/M2 regressions**
plus **34 framework tests**, with zero failures, errors or skips. Actual JUnit and its manifest are
preserved in `results/m3a/regression/`. Tests include positive observation calibration for B01–B05,
duplicate-class counting, false-positive arithmetic, legitimate over-denial, wrong-content functional
errors, failed startup/setup/transport, missing DB evidence, modified checksums, whole-run aborts,
credential redaction and replay. A denial or 5xx with a forbidden persisted update remains a violation.

Ruff lint/formatting and whitespace checks passed. The existing Compose configuration validated;
its network settings were not changed. Images built with the previously documented cloud CA-secret
adaptation, retaining TLS verification. No new runtime/development dependencies were added.
One existing Starlette warning about HTTPX-backed TestClient deprecation remains unsuppressed.

All five derived outputs—metrics JSON, evaluation JSON, CSV, JUnit and Markdown—regenerated
byte-for-byte from preserved v2 observations and the run's own frozen inventory. The preserved v1
run remains a failure: 55/56 passed because E5's initial oracle list order was wrong. Its exact
versioned correction is documented in amendments.md; no expected denial or authorization assertion
was weakened, and the failed evidence was not replaced.
CSV files retain the standard CRLF records emitted by Python's CSV writer; `.gitattributes`
recognizes those endings without rewriting the preserved artifact bytes.

## Evidence and reproduction

Follow reproduction.md for the exact local workflow. The important commands after image/database
setup are:

```sh
.venv/bin/python scripts/run_evaluation.py --output results/m3a/runs/new-run
.venv/bin/python -m bola_lab.evaluation.reports results/m3a/runs/new-run
docker compose --profile test run --rm test
```

The first command requires the explicit synthetic `BOLA_EVALUATION_DATABASE_URL` described in that
guide. Output directories cannot already exist. Raw observations and inventory/fixture checksums
are in each run directory; execution error records and completeness are retained. Passwords, issued
tokens, hashes/digests and sensitive authentication details were checked absent from run artifacts.
Regressions and evaluation use different disposable databases. Existing M1/M2 evidence is preserved.

Hosted CI runs regressions, the live inventory, and replay validation on the exact pushed commit.
Its result must be checked in GitHub Actions; local success is not a substitute for hosted success.
Artifacts uploaded by the workflow include actual regression JUnit and sanitized live evidence.

## Limitations and stopping point

The detector shares some scope checks with the independent contract evaluator; the zero false-positive
result on this small corpus is not independent statistical validation. Synthetic labelled positive
observation tests establish calibration behavior, not empirical recall. There is no defective or
centralized configuration comparison, broad concurrency/load study, performance claim or external
target testing. Ordinary local Docker setup outside this cloud proxy environment remains for the
user to verify. Existing lab credentials, administrative DB role and absent production controls make
the application local-only. M3-A stops here; further implementations require explicit approval.
