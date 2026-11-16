"""Regenerate all derived reports from checksummed, sanitized independent observations."""

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from bola_lab.evaluation.checks import evaluate
from bola_lab.evaluation.models import DEFECTS, digest, read_frozen, scenarios


def fraction(numerator, denominator, planned, excluded):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
        "planned_eligible": planned,
        "excluded_ids": excluded,
        "complete": denominator == planned,
    }


def summarize(specs, observations, evaluations, run_errors=()):
    by_id = {row["scenario_id"]: row for row in evaluations}
    raw = {row["scenario_id"]: row for row in observations}
    auth = [s for s in specs if s.category == "authorization"]
    decisive = [s for s in auth if by_id[s.id]["enforcement"] != "inconclusive"]
    # A proven forbidden effect remains a violation even when HTTP execution returned an error.
    enforcement = fraction(
        sum(by_id[s.id]["enforcement"] == "compliant" for s in decisive),
        len(decisive),
        len(auth),
        [s.id for s in auth if s not in decisive],
    )
    denied = [s for s in auth if s.expected["permission"] == "deny"]
    denied_decisive = [s for s in denied if s in decisive]
    unauthorized = fraction(
        sum(by_id[s.id]["enforcement"] == "unauthorized_success" for s in denied_decisive),
        len(denied_decisive),
        len(denied),
        [s.id for s in denied if s not in denied_decisive],
    )
    allowed = [s for s in auth if s.expected["permission"] == "allow"]
    allowed_complete = [
        s
        for s in allowed
        if not by_id[s.id]["execution_errors"]
        and raw[s.id].get("response") is not None
        and raw[s.id].get("after") is not None
    ]
    legitimate = fraction(
        sum(by_id[s.id]["status"] == "passed" for s in allowed_complete),
        len(allowed_complete),
        len(allowed),
        [s.id for s in allowed if s not in allowed_complete],
    )
    controls = [s for s in specs if s.permitted_control]
    # Predeclared allowed requests are not automatically negative detector controls.
    # Confirm actual behavior independently; expose every invalidated control.
    valid_controls = [
        s
        for s in controls
        if by_id[s.id]["functional_pass"] and by_id[s.id]["enforcement"] == "compliant"
    ]
    fpr = fraction(
        sum(by_id[s.id]["detector"]["verdict"] == "finding" for s in valid_controls),
        len(valid_controls),
        len(controls),
        [s.id for s in controls if s not in valid_controls],
    )
    observed_classes = sorted({c for row in evaluations for c in row["detector"]["classes"]})
    counts = Counter(row["status"] for row in evaluations)
    errors = [s.id for s in specs if by_id[s.id]["execution_errors"]]
    return {
        "schema_version": 1,
        "implementation": "endpoint-specific",
        "evidence_kind": "executed defensive API evaluation",
        "counts": {
            "planned": len(specs),
            "request_attempted": sum(bool(r.get("request_sent")) for r in observations),
            "http_responses_received": sum(r.get("response") is not None for r in observations),
            "passed": counts["passed"],
            "failed": counts["failed"],
            "inconclusive": counts["inconclusive"],
            "execution_error_ids": errors,
            "run_error_count": len(run_errors),
        },
        "category_counts": dict(Counter(s.category for s in specs)),
        "authorization_enforcement_accuracy": enforcement,
        "unauthorized_operation_success_rate": unauthorized,
        "legitimate_operation_success_rate": legitimate,
        "detector_false_positive_rate": fpr,
        "live_seeded_defect_recall": {
            "numerator": 0,
            "denominator": 0,
            "value": None,
            "planned_inventory_total": len(DEFECTS),
            "known_present_evaluated": [],
            "reason": "No labelled defective API configuration evaluated in M3-A",
        },
        "detector_findings": {
            "observation_count": sum(r["detector"]["verdict"] == "finding" for r in evaluations),
            "distinct_observed_classes": observed_classes,
            "distinct_observed_class_count": len(observed_classes),
        },
        "run_complete": not run_errors and not errors and counts["inconclusive"] == 0,
        "run_passed": not run_errors and counts["passed"] == len(specs) and not errors,
    }


def regenerate(directory: Path):
    manifest = json.loads((directory / "manifest.json").read_text())
    if (
        manifest["configuration"] != "hardened"
        or manifest["implementation"] != "endpoint-specific"
        or manifest["known_present_seeded_defects"]
    ):
        raise ValueError("M3-A reports support only the existing defensive API evaluation")
    inventory = read_frozen("inventory.json", directory)
    read_frozen("fixture.json", directory)
    if (
        digest(directory / "inventory.json") != manifest["inventory_sha256"]
        or digest(directory / "fixture.json") != manifest["fixture_sha256"]
        or digest(directory / "observations.jsonl") != manifest["observations_sha256"]
    ):
        raise ValueError("Evidence checksum mismatch")
    specs = scenarios(inventory)
    observations = [
        json.loads(line) for line in (directory / "observations.jsonl").read_text().splitlines()
    ]
    by_id = {r["scenario_id"]: r for r in observations}
    if len(by_id) != len(observations) or set(by_id) != {s.id for s in specs}:
        raise ValueError("Missing, duplicate or unknown observation IDs")
    if any(r["inventory_sha256"] != manifest["inventory_sha256"] for r in observations):
        raise ValueError("Observation belongs to another inventory")
    evaluations = [evaluate(spec, by_id[spec.id]) for spec in specs]
    metrics = summarize(specs, observations, evaluations, manifest["errors"])
    for name, value in (("evaluations.json", evaluations), ("metrics.json", metrics)):
        (directory / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    fields = [
        "scenario_id",
        "actor_id",
        "category",
        "method",
        "path",
        "expected_permission",
        "expected_status",
        "actual_status",
        "status",
        "enforcement",
        "functional_pass",
        "detector_verdict",
        "defect_classes",
        "execution_errors",
    ]
    with (directory / "observations.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for spec, result in zip(specs, evaluations, strict=True):
            observation = by_id[spec.id]
            writer.writerow(
                {
                    "scenario_id": spec.id,
                    "actor_id": spec.actor_id,
                    "category": spec.category,
                    "method": spec.request["method"],
                    "path": spec.request["path"],
                    "expected_permission": spec.expected["permission"],
                    "expected_status": spec.expected["status"],
                    "actual_status": (observation.get("response") or {}).get("status"),
                    "status": result["status"],
                    "enforcement": result["enforcement"],
                    "functional_pass": result["functional_pass"],
                    "detector_verdict": result["detector"]["verdict"],
                    "defect_classes": ",".join(result["detector"]["classes"]),
                    "execution_errors": json.dumps(result["execution_errors"], sort_keys=True),
                }
            )
    suite = ET.Element(
        "testsuite",
        name="M3-A real HTTP authorization scenarios",
        tests=str(len(specs)),
        failures=str(metrics["counts"]["failed"]),
        errors=str(metrics["counts"]["inconclusive"]),
        skipped="0",
    )
    for result in evaluations:
        case = ET.SubElement(
            suite, "testcase", classname="evaluation.live_http", name=result["scenario_id"]
        )
        if result["status"] != "passed":
            ET.SubElement(
                case,
                "error" if result["status"] == "inconclusive" else "failure",
                message=result["enforcement"],
            ).text = json.dumps(result, sort_keys=True)
    ET.ElementTree(suite).write(directory / "junit.xml", encoding="utf-8", xml_declaration=True)
    commit = (manifest.get("source") or {}).get("commit", "unavailable")
    lines = [
        "# M3-A defensive API evaluation",
        "",
        f"Source commit: `{commit}`.",
        f"Inventory SHA-256: `{manifest['inventory_sha256']}`.",
        "",
        "Only endpoint-specific authorization was evaluated. No seeded-defect recall "
        "or three-configuration comparison is claimed.",
        "",
        f"Run complete: **{metrics['run_complete']}**. Run passed: **{metrics['run_passed']}**.",
        "",
        f"Planned: {len(specs)}; "
        f"responses received: {metrics['counts']['http_responses_received']}; "
        f"passed: {metrics['counts']['passed']}; failed: {metrics['counts']['failed']}; "
        f"inconclusive: {metrics['counts']['inconclusive']}.",
        "",
        "| Measure | Numerator | Denominator | Value | Complete |",
        "|---|---:|---:|---:|---|",
    ]
    for name in (
        "authorization_enforcement_accuracy",
        "unauthorized_operation_success_rate",
        "legitimate_operation_success_rate",
        "detector_false_positive_rate",
        "live_seeded_defect_recall",
    ):
        row = metrics[name]
        value = "unavailable" if row["value"] is None else f"{row['value']:.2%}"
        lines.append(
            f"| {name} | {row['numerator']} | {row['denominator']} | {value} | "
            f"{row.get('complete', 'not evaluated')} |"
        )
    lines += [
        "",
        "Rates describe eligible observations only. Consult metrics.json for excluded IDs "
        "and execution errors.",
        "Detector calibration fixtures are unit tests, not live API evidence. "
        "An incorrect legitimate denial is not automatically a detector false positive.",
        "",
        "| ID | Functional result | Enforcement | Detector |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {r['scenario_id']} | {r['status']} | {r['enforcement']} | {r['detector']['verdict']} |"
        for r in evaluations
    )
    (directory / "summary.md").write_text("\n".join(lines) + "\n")
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(regenerate(args.directory), indent=2))


if __name__ == "__main__":
    main()
