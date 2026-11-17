"""Independent test authority. The builder never imports this module and never
sees its cases. The oracle checks the resulting RECORDS (destination evidence),
not what the workflow or the model claims it did."""

from . import workflow


def run_case(wf: dict, shipments: list[dict], case: dict) -> dict:
    try:
        result = workflow.execute(wf, shipments, case["updates"])
    except workflow.InvalidWorkflow as e:
        return {"name": case["name"], "passed": False, "problems": [f"invalid workflow: {e}"]}

    before = {s["shipment_id"]: s["status"] for s in shipments}
    after = {s["shipment_id"]: s["status"] for s in result["db"]}
    newly_delivered = sorted(sid for sid in after if after[sid] == "delivered" and before[sid] != "delivered")
    flagged = sorted({e["update"] for e in result["effects"] if e["effect"] == "flagged"})
    delivered_effects = [e for e in result["effects"] if e["effect"] == "delivered"]

    exp = case["expected"]
    problems = []
    if newly_delivered != sorted(exp["delivered"]):
        problems.append(f"records marked delivered: {newly_delivered}, expected {sorted(exp['delivered'])}")
    if flagged != sorted(exp["flagged"]):
        problems.append(f"flagged: {flagged}, expected {sorted(exp['flagged'])}")
    if len(delivered_effects) != len({e['record'] for e in delivered_effects}):
        problems.append("duplicate delivered effect on the same record")
    return {"name": case["name"], "source": case.get("source", "local"), "passed": not problems,
            "problems": problems, "effects": result["effects"]}


def run_suite(wf: dict, shipments: list[dict], cases: list[dict]) -> list[dict]:
    return [run_case(wf, shipments, c) for c in cases]
