"""Typed workflow format + deterministic executor.

The model only PROPOSES a workflow (JSON). Execution is deterministic code:
no model is called while a workflow runs, and unsupported operations are rejected.
"""

import copy

MATCH_FIELDS = {"shipment_id", "customer_name", "carrier_name"}
ACTIONS = {"mark_delivered", "flag_exception", "skip"}
CONDITION_FIELDS = {"status", "customer_name", "carrier_name"}

SCHEMA_DOC = """{
  "match_by": one of ["shipment_id", "customer_name", "carrier_name"],
  "rules": [  // checked in order against the MATCHED shipment record; first match wins
    {"when": {"field": one of ["status", "customer_name", "carrier_name"], "equals": <string>},
     "action": one of ["mark_delivered", "flag_exception", "skip"]}
  ],
  "default_action": one of ["mark_delivered", "flag_exception", "skip"],
  "explanation": <short string>
}
Executor behavior (fixed, not configurable): if the match finds 0 or 2+ shipments, the update is flagged.
mark_delivered on an already-delivered shipment changes nothing."""


class InvalidWorkflow(ValueError):
    pass


def validate(wf: dict) -> dict:
    if not isinstance(wf, dict):
        raise InvalidWorkflow("workflow must be an object")
    if wf.get("match_by") not in MATCH_FIELDS:
        raise InvalidWorkflow(f"unsupported match_by: {wf.get('match_by')!r}")
    if wf.get("default_action") not in ACTIONS:
        raise InvalidWorkflow(f"unsupported default_action: {wf.get('default_action')!r}")
    rules = wf.get("rules", [])
    if not isinstance(rules, list) or len(rules) > 10:
        raise InvalidWorkflow("rules must be a list of at most 10")
    for r in rules:
        when = r.get("when", {})
        if when.get("field") not in CONDITION_FIELDS or not isinstance(when.get("equals"), str):
            raise InvalidWorkflow(f"unsupported rule condition: {when!r}")
        if r.get("action") not in ACTIONS:
            raise InvalidWorkflow(f"unsupported rule action: {r.get('action')!r}")
    return {"match_by": wf["match_by"], "rules": rules, "default_action": wf["default_action"],
            "explanation": str(wf.get("explanation", ""))[:500]}


def execute(wf: dict, shipments: list[dict], updates: list[dict]) -> dict:
    """Run on a disposable copy. Returns the resulting records plus an effect log."""
    wf = validate(wf)
    db = copy.deepcopy(shipments)
    effects = []
    for u in updates:
        key = wf["match_by"]
        matches = [s for s in db if s[key] == u.get(key)]
        if len(matches) != 1:
            effects.append({"update": u["shipment_id"], "effect": "flagged", "reason": f"{len(matches)} matches on {key}"})
            continue
        s = matches[0]
        action = wf["default_action"]
        for r in wf["rules"]:
            if s.get(r["when"]["field"]) == r["when"]["equals"]:
                action = r["action"]
                break
        if action == "mark_delivered":
            if s["status"] != "delivered":
                s["status"] = "delivered"
                effects.append({"update": u["shipment_id"], "effect": "delivered", "record": s["shipment_id"]})
        elif action == "flag_exception":
            effects.append({"update": u["shipment_id"], "effect": "flagged", "record": s["shipment_id"]})
    return {"db": db, "effects": effects}
