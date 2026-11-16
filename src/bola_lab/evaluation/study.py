"""Versioned three-treatment HTTP experiment; historical artifacts are preserved."""

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import tarfile
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import psycopg

from bola_lab.db import connect
from bola_lab.evaluation import detector, truth
from bola_lab.evaluation.models import PACKAGE, digest, read_frozen, scenarios
from bola_lab.evaluation.runner import evaluation_settings, execute, live_server, now, provenance
from bola_lab.migrations import migrate

TREATMENTS = ("baseline", "endpoint", "centralized")
ARTIFACTS = (
    "inventory.json",
    "supplement.json",
    "fixture.json",
    "registry.json",
    "baseline-profile.json",
)


def rate(n, d, planned, excluded=()):
    return {
        "numerator": n,
        "denominator": d,
        "value": n / d if d else None,
        "planned": planned,
        "excluded_ids": list(excluded),
        "complete": d == planned,
    }


def group_metrics(specs, raw, evaluated, labels, controls):
    auth = [s for s in specs if s.category == "authorization"]
    decisive = [s for s in auth if evaluated[s.id]["enforcement"] != "inconclusive"]
    denied = [s for s in auth if s.expected["permission"] == "deny"]
    denied_ok = [s for s in denied if s in decisive]
    permitted = [s for s in auth if s.expected["permission"] == "allow"]
    permitted_ok = [
        s
        for s in permitted
        if not raw[s.id].get("errors")
        and raw[s.id].get("after") is not None
        and raw[s.id].get("response") is not None
    ]
    selected_controls = [s for s in specs if s.id in controls]
    negatives = [
        s
        for s in selected_controls
        if evaluated[s.id]["functional_pass"] and evaluated[s.id]["enforcement"] == "compliant"
    ]
    verified = [r["defect_id"] for r in labels.get("labels", []) if r["verified_present"]]
    found = sorted(
        {
            d
            for s in specs
            for d in evaluated[s.id]["detector"]["classes"]
            if evaluated[s.id]["enforcement"] == "unauthorized_success"
        }
    )
    return {
        "scenario_count": len(specs),
        "authorization_eligible": len(auth),
        "enforcement_accuracy": rate(
            sum(evaluated[s.id]["enforcement"] == "compliant" for s in decisive),
            len(decisive),
            len(auth),
            [s.id for s in auth if s not in decisive],
        ),
        "unauthorized_operation_success": rate(
            sum(evaluated[s.id]["enforcement"] == "unauthorized_success" for s in denied_ok),
            len(denied_ok),
            len(denied),
            [s.id for s in denied if s not in denied_ok],
        ),
        "legitimate_operation_success": rate(
            sum(evaluated[s.id]["status"] == "passed" for s in permitted_ok),
            len(permitted_ok),
            len(permitted),
            [s.id for s in permitted if s not in permitted_ok],
        ),
        "false_positive_rate": rate(
            sum(evaluated[s.id]["detector"]["verdict"] == "finding" for s in negatives),
            len(negatives),
            len(selected_controls),
            [s.id for s in selected_controls if s not in negatives],
        ),
        "recall": rate(
            len(set(found) & set(verified)), len(verified), len(labels.get("labels", []))
        ),
        "recall_status": "measured_on_independently_verified_live_seeds"
        if verified
        else "not_applicable_no_known_present_defects",
        "distinct_verified_defects": verified,
        "distinct_detected_verified_defects": sorted(set(found) & set(verified)),
        "disclosure_scenarios": [s.id for s in specs if evaluated[s.id]["disclosures"]],
        "mutation_scenarios": [s.id for s in specs if evaluated[s.id]["mutations"]],
        "scope_violations_during_permitted_requests": [
            s.id for s in permitted if evaluated[s.id]["enforcement"] == "unauthorized_success"
        ],
        "normative_passed": sum(evaluated[s.id]["status"] == "passed" for s in specs),
        "normative_failed": sum(evaluated[s.id]["status"] == "failed" for s in specs),
        "inconclusive_ids": [s.id for s in specs if evaluated[s.id]["status"] == "inconclusive"],
        "execution_error_ids": [s.id for s in specs if raw[s.id].get("errors")],
        "unexecuted_ids": [s.id for s in specs if not raw[s.id].get("request_sent")],
    }


def regenerate(directory: Path, *, charts=True):
    manifest = json.loads((directory / "manifest.json").read_text())
    for name in ARTIFACTS:
        read_frozen(name, directory)
        if digest(directory / name) != manifest["artifacts_sha256"][name]:
            raise ValueError("Artifact hash mismatch")
    core = scenarios(read_frozen("inventory.json", directory))
    supplement = scenarios(read_frozen("supplement.json", directory))
    specs = core + supplement
    registry = read_frozen("registry.json", directory)
    profile = read_frozen("baseline-profile.json", directory)
    comparison = {
        "evaluator_version": registry["evaluator_version"],
        "treatments": {},
        "counts": {},
        "run_passed": not manifest["errors"].get("run"),
    }
    for treatment in TREATMENTS:
        folder = directory / treatment
        if digest(folder / "observations.jsonl") != manifest["observations_sha256"][treatment]:
            raise ValueError("Raw evidence hash mismatch")
        records = [
            json.loads(line) for line in (folder / "observations.jsonl").read_text().splitlines()
        ]
        raw = {r["scenario_id"]: r for r in records}
        if len(raw) != len(records) or set(raw) != {s.id for s in specs}:
            raise ValueError("Observation coverage mismatch")
        if any(
            r["source_commit"] != manifest["source"]["commit"] or r["treatment"] != treatment
            for r in records
        ):
            raise ValueError("Observation provenance mismatch")
        labels = {"labels": [], "all_verified": True}
        if treatment == "baseline":
            from laboratory.witness import verify

            labels = verify(records)
            labels["source_commit"] = manifest["source"]["commit"]
            for item in labels["labels"]:
                item["observation_sha256"] = hashlib.sha256(
                    json.dumps(raw[item["witness_scenario"]], sort_keys=True).encode()
                ).hexdigest()
        # Known-present verification happens before detector output or recall is computed.
        (folder / "labels.json").write_text(json.dumps(labels, indent=2, sort_keys=True) + "\n")
        evaluated = {}
        for s in specs:
            result = truth.evaluate(s, raw[s.id])
            result["detector"] = detector.detect(s, raw[s.id])
            expected_violation = (
                treatment == "baseline" and s.id in profile["expected_violation_ids"]
            )
            if expected_violation:
                experimental = s.model_copy(deep=True)
                experimental.expected = deepcopy(profile["profiles"][s.id])
                profile_ok = truth.contract(experimental, raw[s.id])
                verified = result["enforcement"] == "unauthorized_success" and profile_ok
            else:
                verified = result["status"] == "passed"
            result.update(
                expected_seed_observation=expected_violation,
                verification_passed=verified,
                evidence={
                    "scenario_id": s.id,
                    "observation_file": f"{treatment}/observations.jsonl",
                    "source_commit": manifest["source"]["commit"],
                    "treatment": treatment,
                },
            )
            evaluated[s.id] = result
        (folder / "evaluations.json").write_text(
            json.dumps(list(evaluated.values()), indent=2, sort_keys=True) + "\n"
        )
        metrics = {
            "core": group_metrics(core, raw, evaluated, labels, registry["negative_controls"]),
            "supplement": group_metrics(supplement, raw, evaluated, {}, []),
            "unexpected_functional_regressions": [
                s.id for s in specs if not evaluated[s.id]["verification_passed"]
            ],
            "verification_passed": all(r["verification_passed"] for r in evaluated.values())
            and labels["all_verified"],
        }
        if manifest["errors"].get(treatment):
            metrics["verification_passed"] = False
        (folder / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
        suite = ET.Element(
            "testsuite",
            name=treatment + " experimental verification (not policy compliance)",
            tests=str(len(specs)),
            failures=str(sum(not r["verification_passed"] for r in evaluated.values())),
            errors="0",
            skipped="0",
        )
        with (folder / "comparison.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                [
                    "scenario_id",
                    "expected_permission",
                    "actual_status",
                    "normative_result",
                    "enforcement",
                    "detector",
                    "expected_seed_observation",
                    "verification_passed",
                ]
            )
            for s in specs:
                r = evaluated[s.id]
                writer.writerow(
                    [
                        s.id,
                        s.expected["permission"],
                        (raw[s.id].get("response") or {}).get("status"),
                        r["status"],
                        r["enforcement"],
                        ",".join(r["detector"]["classes"]),
                        r["expected_seed_observation"],
                        r["verification_passed"],
                    ]
                )
                case = ET.SubElement(suite, "testcase", classname="study." + treatment, name=s.id)
                properties = ET.SubElement(case, "properties")
                ET.SubElement(
                    properties, "property", name="normative_enforcement", value=r["enforcement"]
                )
                if not r["verification_passed"]:
                    ET.SubElement(case, "failure", message=r["enforcement"]).text = json.dumps(
                        r, sort_keys=True
                    )
        ET.ElementTree(suite).write(folder / "junit.xml", encoding="utf-8", xml_declaration=True)
        comparison["treatments"][treatment] = metrics
        comparison["run_passed"] &= metrics["verification_passed"]
    comparison["counts"] = {
        "planned": len(specs) * len(TREATMENTS),
        "core_per_treatment": len(core),
        "supplement_per_treatment": len(supplement),
    }
    (directory / "comparison.json").write_text(
        json.dumps(comparison, sort_keys=True, indent=2) + "\n"
    )
    lines = [
        "# Executed security treatment comparison",
        "",
        f"Source: `{manifest['source']['commit']}`; evaluator: `{registry['evaluator_version']}`.",
        "Normative policy is identical across treatments. Expected seeded violations remain "
        "policy failures even when experimental verification passes.",
        "",
        "| Treatment | Enforcement | Prohibited success | Legitimate success | "
        "Detector FP | Live seeded recall |",
        "|---|---|---|---|---|---|",
    ]
    for name, metrics in comparison["treatments"].items():
        values = []
        for key in (
            "enforcement_accuracy",
            "unauthorized_operation_success",
            "legitimate_operation_success",
            "false_positive_rate",
            "recall",
        ):
            row = metrics["core"][key]
            values.append(
                f"{row['numerator']}/{row['denominator']}"
                if row["value"] is not None
                else "not applicable"
            )
        lines.append("| " + name + " | " + " | ".join(values) + " |")
    lines += [
        "",
        "Core metrics use only the frozen 56-case core; "
        "supplement metrics are separate in comparison.json.",
        "False-positive controls are the same preregistered compliant controls for each treatment. "
        "Calibration examples are excluded.",
        "No causal superiority of centralized over correct endpoint authorization "
        "is inferred from equal defensive outcomes.",
    ]
    (directory / "comparison.md").write_text("\n".join(lines) + "\n")
    if charts and comparison["run_passed"]:
        make_charts(directory, comparison)
    return comparison


def make_charts(directory, comparison):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams.update({"svg.hashsalt": "bola-study-1", "font.size": 10})
    names = list(TREATMENTS)
    # Deterministic standalone scientific charts, derived solely from recorded comparison data.
    fig, ax = plt.subplots(figsize=(8, 4))
    for offset, metric, label in [
        (-0.18, "unauthorized_operation_success", "Prohibited operation success"),
        (0.18, "legitimate_operation_success", "Legitimate operation success"),
    ]:
        rows = [comparison["treatments"][n]["core"][metric] for n in names]
        bars = ax.bar(
            [i + offset for i in range(3)], [r["value"] or 0 for r in rows], width=0.35, label=label
        )
        ax.bar_label(bars, labels=[f"{r['numerator']}/{r['denominator']}" for r in rows], padding=3)
    ax.set(
        xticks=range(3),
        xticklabels=names,
        ylim=(0, 1.18),
        ylabel="Rate",
        title="Core operation outcomes (actual numerators/denominators)",
    )
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(directory / "operation-outcomes.svg", metadata={"Date": None})
    fig.savefig(directory / "operation-outcomes.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    for offset, key, label in [
        (-0.18, "disclosure_scenarios", "Confirmed disclosure scenarios"),
        (0.18, "mutation_scenarios", "Confirmed mutation scenarios"),
    ]:
        values = [len(comparison["treatments"][n]["core"][key]) for n in names]
        bars = ax.bar([i + offset for i in range(3)], values, width=0.35, label=label)
        ax.bar_label(bars, padding=3)
    ax.set(
        xticks=range(3),
        xticklabels=names,
        ylabel="Scenario count",
        title="Confirmed core violations (not distinct defect counts)",
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(directory / "confirmed-violations.svg", metadata={"Date": None})
    fig.savefig(directory / "confirmed-violations.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = json.loads((directory / "baseline" / "labels.json").read_text())["labels"]
    detected = comparison["treatments"]["baseline"]["core"]["distinct_detected_verified_defects"]
    bars = ax.bar(
        [r["defect_id"] for r in labels],
        [int(r["verified_present"] and r["defect_id"] in detected) for r in labels],
    )
    ax.bar_label(
        bars,
        labels=[
            "detected"
            if r["verified_present"] and r["defect_id"] in detected
            else "not confirmed/detected"
            for r in labels
        ],
        padding=3,
    )
    ax.set(
        ylim=(0, 1.3),
        yticks=[0, 1],
        ylabel="Verified live detection",
        title="Distinct independently verified baseline defects",
    )
    fig.tight_layout()
    fig.savefig(directory / "distinct-defect-detection.svg", metadata={"Date": None})
    fig.savefig(directory / "distinct-defect-detection.png", dpi=160)
    plt.close(fig)


def missing(spec, manifest, treatment):
    return {
        "scenario_id": spec.id,
        "source_commit": manifest["source"]["commit"],
        "treatment": treatment,
        "inventory_sha256": "unexecuted",
        "actor_id": spec.actor_id,
        "request": spec.request,
        "started_at": now(),
        "finished_at": now(),
        "before": None,
        "after": None,
        "response": None,
        "request_sent": False,
        "errors": [{"stage": "not_run", "type": "TreatmentUnavailable"}],
    }


def run(output):
    from bola_lab.evaluation.models import source_hashes

    output.mkdir(parents=True, exist_ok=False)
    specs = scenarios() + scenarios(read_frozen("supplement.json"))
    manifest = {
        "evaluator_version": "study-1",
        "source": {"commit": "unavailable", "source_sha256": source_hashes()},
        "started_at": now(),
        "finished_at": None,
        "artifacts_sha256": {},
        "observations_sha256": {},
        "errors": {},
        "database": "bola_lab_evaluation_test",
    }
    for name in ARTIFACTS:
        for file in (name, name + ".sha256"):
            (output / file).write_bytes((PACKAGE / file).read_bytes())
        manifest["artifacts_sha256"][name] = digest(PACKAGE / name)
    combined = hashlib.sha256("".join(manifest["artifacts_sha256"].values()).encode()).hexdigest()
    try:
        manifest["source"] = provenance()
        settings = evaluation_settings(os.environ["BOLA_EVALUATION_DATABASE_URL"])
        with psycopg.connect(
            settings.database_url.get_secret_value(), autocommit=True, connect_timeout=5
        ) as lock:
            if not lock.execute("SELECT pg_try_advisory_lock(3123056)").fetchone()[0]:
                raise RuntimeError("Evaluation database already in use")
            migrate(settings)
            with connect(settings) as conn:
                manifest["postgres_version"] = conn.execute("SHOW server_version").fetchone()[
                    "server_version"
                ]
                manifest["database_oid"] = conn.execute(
                    "SELECT oid FROM pg_database WHERE datname=current_database()"
                ).fetchone()["oid"]
            for treatment in TREATMENTS:
                folder = output / treatment
                folder.mkdir()
                records = []
                manifest["errors"][treatment] = []
                with (folder / "observations.jsonl").open("w") as stream:
                    try:
                        with live_server(settings, treatment) as client:
                            for spec in specs:
                                record = execute(spec, settings, client, combined)
                                record.update(
                                    source_commit=manifest["source"]["commit"], treatment=treatment
                                )
                                records.append(record)
                                stream.write(json.dumps(record, sort_keys=True) + "\n")
                                stream.flush()
                    except Exception as error:
                        manifest["errors"][treatment].append(
                            {"stage": "treatment_execution", "type": type(error).__name__}
                        )
                    seen = {r["scenario_id"] for r in records}
                    for spec in specs:
                        if spec.id not in seen:
                            stream.write(
                                json.dumps(missing(spec, manifest, treatment), sort_keys=True)
                                + "\n"
                            )
    except Exception as error:
        manifest["errors"]["run"] = [{"stage": "run_setup", "type": type(error).__name__}]
    for treatment in TREATMENTS:
        folder = output / treatment
        folder.mkdir(exist_ok=True)
        if not (folder / "observations.jsonl").exists():
            (folder / "observations.jsonl").write_text(
                "".join(
                    json.dumps(missing(spec, manifest, treatment), sort_keys=True) + "\n"
                    for spec in specs
                )
            )
        manifest["observations_sha256"][treatment] = digest(folder / "observations.jsonl")
    manifest["finished_at"] = now()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return regenerate(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--stream-archive", action="store_true")
    args = parser.parse_args()
    result = regenerate(args.output) if args.replay else run(args.output)
    if args.stream_archive:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for path in sorted(args.output.rglob("*")):
                if path.is_file():
                    archive.add(path, arcname=str(path.relative_to(args.output)))
        print(
            "BOLA_EVIDENCE_BEGIN\n"
            + base64.b64encode(buffer.getvalue()).decode()
            + "\nBOLA_EVIDENCE_END"
        )
    else:
        print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["run_passed"] else 1)


if __name__ == "__main__":
    main()
