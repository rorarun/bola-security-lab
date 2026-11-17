"""Task BOLA detector. Does not import the independent ground-truth evaluator."""


def detect(spec, observation):
    before, after = observation.get("before"), observation.get("after")
    response = observation.get("response")
    if spec.category != "authorization" or "/tasks" not in spec.request["path"]:
        return {"verdict": "not_applicable", "classes": []}
    findings = set()
    denied = spec.expected["permission"] == "deny"
    if before is not None and response is not None and spec.request["method"] == "GET":
        payload = response["body"]
        rows = payload if isinstance(payload, list) else [payload]
        expected = spec.expected["response"]
        expected_rows = expected if isinstance(expected, list) else [expected]
        allowed_ids = {r["id"] for r in expected_rows if isinstance(r, dict) and "id" in r}
        for row in rows:
            if not isinstance(row, dict):
                continue
            known = next(
                (
                    t
                    for t in before["tasks"]
                    if t.get("id") == row.get("id") and t["title"] == row.get("title")
                ),
                None,
            )
            if known and (denied or known["id"] not in allowed_ids):
                findings.add("B02" if spec.request["path"].endswith("/tasks") else "B01")
    if before is not None and after is not None and denied:
        initial = {r["id"]: r for r in before["tasks"]}
        final = {r["id"]: r for r in after["tasks"]}
        if final.keys() - initial.keys():
            findings.add("B05")
        if initial.keys() - final.keys():
            findings.add("B04")
        if any(initial[k] != final[k] for k in initial.keys() & final.keys()):
            findings.add("B03")
    complete = (
        before is not None
        and after is not None
        and response is not None
        and not observation.get("errors")
    )
    return {
        "verdict": "finding" if findings else "no_finding" if complete else "inconclusive",
        "classes": sorted(findings),
    }
