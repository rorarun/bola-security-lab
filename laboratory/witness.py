"""Literal primary witnesses verify known-present labels independently of detector/oracle code."""

import hashlib
from pathlib import Path


def verify(records):
    by_id = {r["scenario_id"]: r for r in records}
    results = []
    for defect, id in (("B01", "N2"), ("B02", "L4"), ("B03", "N4"), ("B04", "N5"), ("B05", "N3")):
        r = by_id[id]
        before, after, response = r.get("before"), r.get("after"), r.get("response")
        valid = bool(before and after and response and not r["errors"] and r["actor_id"] == 4)
        if valid:
            valid &= not any(
                m["project_id"] == 1 and m["user_id"] == 4 for m in before["project_memberships"]
            )
            original = next(t for t in before["tasks"] if t["id"] == 1)
            if defect == "B01":
                valid &= response["status"] == 200 and response["body"] == original
            elif defect == "B02":
                valid &= response["status"] == 200 and original in response["body"]
            elif defect == "B03":
                changed = next(t for t in after["tasks"] if t["id"] == 1)
                valid &= (
                    response["status"] == 200
                    and changed["title"] == "Forbidden"
                    and changed["title"] != original["title"]
                )
            elif defect == "B04":
                valid &= response["status"] == 204 and not any(t["id"] == 1 for t in after["tasks"])
            else:
                valid &= response["status"] == 201 and any(
                    t["id"] == 4
                    and t["organization_id"] == 1
                    and t["project_id"] == 1
                    and t["created_by"] == 4
                    for t in after["tasks"]
                )
        results.append(
            {"defect_id": defect, "witness_scenario": id, "verified_present": bool(valid)}
        )
    return {
        "method": "literal independent HTTP/state witnesses plus source-labelled omissions",
        "source_sha256": hashlib.sha256(
            Path(__file__).with_name("app.py").read_bytes()
        ).hexdigest(),
        "labels": results,
        "all_verified": all(r["verified_present"] for r in results),
    }
