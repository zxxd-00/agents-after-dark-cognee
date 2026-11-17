"""Synthetic logistics data. No real company data anywhere.

Task: carriers send delivery confirmations. Match each one to the right shipment
record and mark it delivered — or flag it for a human.

Construction examples are deliberately easy (every name is unique).
Fresh test cases are kept separate and contain realistic exceptions.
"""

# ---- Workspace A: "Bayline Freight" (the demo company) ----
SHIPMENTS_A = [
    {"shipment_id": "BF-1001", "customer_name": "Harbor Foods", "carrier_name": "Swift Haul", "status": "in_transit"},
    {"shipment_id": "BF-1002", "customer_name": "Peak Outdoor", "carrier_name": "Blue Line", "status": "in_transit"},
    {"shipment_id": "BF-1003", "customer_name": "Delta Pharma", "carrier_name": "Swift Haul", "status": "in_transit"},
    # Two different shipments for the same customer, same carrier: the hard case.
    {"shipment_id": "BF-1004", "customer_name": "Acme Supply", "carrier_name": "Blue Line", "status": "in_transit"},
    {"shipment_id": "BF-1005", "customer_name": "Acme Supply", "carrier_name": "Blue Line", "status": "in_transit"},
    {"shipment_id": "BF-1006", "customer_name": "Nova Retail", "carrier_name": "Coastal", "status": "cancelled"},
]

# Used ONLY by the builder.
CONSTRUCTION_EXAMPLES = [
    {"update": {"shipment_id": "BF-1001", "customer_name": "Harbor Foods", "carrier_name": "Swift Haul", "event": "delivered"},
     "expected": {"delivered": ["BF-1001"], "flagged": []}},
    {"update": {"shipment_id": "BF-1002", "customer_name": "Peak Outdoor", "carrier_name": "Blue Line", "event": "delivered"},
     "expected": {"delivered": ["BF-1002"], "flagged": []}},
]

# Used ONLY by the independent tester. The builder never sees these.
FRESH_TESTS_A = [
    {"name": "simple confirmation",
     "updates": [{"shipment_id": "BF-1003", "customer_name": "Delta Pharma", "carrier_name": "Swift Haul", "event": "delivered"}],
     "expected": {"delivered": ["BF-1003"], "flagged": []}},
    {"name": "same customer, two shipments (must match by ID)",
     "updates": [{"shipment_id": "BF-1005", "customer_name": "Acme Supply", "carrier_name": "Blue Line", "event": "delivered"}],
     "expected": {"delivered": ["BF-1005"], "flagged": []}},
    {"name": "duplicate confirmation must not double-apply",
     "updates": [{"shipment_id": "BF-1004", "customer_name": "Acme Supply", "carrier_name": "Blue Line", "event": "delivered"},
                 {"shipment_id": "BF-1004", "customer_name": "Acme Supply", "carrier_name": "Blue Line", "event": "delivered"}],
     "expected": {"delivered": ["BF-1004"], "flagged": []}},
    {"name": "unknown shipment ID is flagged, not guessed",
     "updates": [{"shipment_id": "BF-9999", "customer_name": "Harbor Foods", "carrier_name": "Swift Haul", "event": "delivered"}],
     "expected": {"delivered": [], "flagged": ["BF-9999"]}},
]

CONFIRMED_RULES_A = [
    "Confirmed rule (human-confirmed by the Bayline ops manager): a carrier delivery confirmation "
    "must be matched to a shipment by the authoritative shipment ID, never by customer name or carrier name.",
]

# ---- Workspace B: "Ridgeway Logistics" (a second, isolated company) ----
# Private records. These must NEVER appear in anything shared with workspace A.
SHIPMENTS_B_PRIVATE = [
    {"shipment_id": "RW-77310", "customer_name": "Ostrander Medical", "carrier_name": "Pinecrest", "status": "cancelled"},
    {"shipment_id": "RW-77311", "customer_name": "Larkfield Bakery", "carrier_name": "Pinecrest", "status": "in_transit"},
]
