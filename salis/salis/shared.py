"""Shared reliability intelligence between isolated workspaces.

Workspace B found a real failure in its own data: carriers sometimes confirm
delivery of a shipment that was CANCELLED. B publishes a generalized, sanitized
failure-test artifact. It contains only synthetic inputs and a generic invariant —
never B's records. Workspace A must opt in, check applicability, and run the test
locally before it can influence anything.
"""

import hashlib
import json

from .data import SHIPMENTS_B_PRIVATE

ALLOWED_KEYS = {"id", "failure_class", "operation_type", "invariant", "fix_pattern",
                "synthetic_case", "limitations", "origin", "revision"}


def _sign(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def build_artifact_from_b() -> dict:
    """What B publishes. The synthetic case uses placeholder IDs, not B's records."""
    body = {
        "id": "lesson-cancelled-confirmation",
        "failure_class": "confirmation_for_cancelled_shipment",
        "operation_type": "carrier_delivery_confirmation",
        "invariant": "A shipment whose status is 'cancelled' must never be marked delivered; it must be flagged for a human.",
        "fix_pattern": "Add a rule: when status equals 'cancelled', action flag_exception.",
        "synthetic_case": {
            "shipments": [{"shipment_id": "SYN-1", "customer_name": "Synthetic Co", "carrier_name": "Synthetic Carrier", "status": "cancelled"}],
            "updates": [{"shipment_id": "SYN-1", "customer_name": "Synthetic Co", "carrier_name": "Synthetic Carrier", "event": "delivered"}],
            "expected": {"delivered": [], "flagged": ["SYN-1"]},
        },
        "limitations": "Applies only to carrier delivery-confirmation workflows with a status field.",
        "origin": "workspace:ridgeway (opted in)",
        "revision": 1,
    }
    return {"body": body, "signature": _sign(body)}


def sanitization_problems(artifact: dict) -> list[str]:
    """Leakage check: nothing from B's private records may appear in the artifact."""
    body = artifact["body"]
    problems = [f"disallowed key: {k}" for k in body if k not in ALLOWED_KEYS]
    text = json.dumps(body)
    for rec in SHIPMENTS_B_PRIVATE:
        for field in ("shipment_id", "customer_name", "carrier_name"):
            if rec[field] in text:
                problems.append(f"private value leaked: {field}")
    return problems


def verify_integrity(artifact: dict) -> bool:
    return _sign(artifact["body"]) == artifact["signature"]


def import_into(artifact: dict, receiving_operation: str, opted_in: bool) -> dict:
    """Returns {'accepted': bool, 'reason': str, 'test_case': ...}."""
    if not opted_in:
        return {"accepted": False, "reason": "receiving workspace has not opted in"}
    if not verify_integrity(artifact):
        return {"accepted": False, "reason": "signature mismatch (tampered)"}
    leaks = sanitization_problems(artifact)
    if leaks:
        return {"accepted": False, "reason": "; ".join(leaks)}
    body = artifact["body"]
    if body["operation_type"] != receiving_operation:
        return {"accepted": False, "reason": "not applicable to this operation"}
    case = dict(body["synthetic_case"])
    case["name"] = f"shared lesson: {body['failure_class']}"
    case["source"] = body["origin"]
    return {"accepted": True, "reason": "ok", "test_case": case, "lesson": body}
