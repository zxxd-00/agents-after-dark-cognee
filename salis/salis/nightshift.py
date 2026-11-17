"""Night Shift: Retrieve memory -> Construct -> Test -> Diagnose -> Repair -> Retest -> Report.

`process_job` is the ONE code path. "Run Now" and the scheduled worker both call it.
"""

import asyncio
import time

from . import shared, store, tester, workflow
from .data import FRESH_TESTS_A, SHIPMENTS_A

MAX_REPAIRS = 2
OPERATION = "carrier_delivery_confirmation"


class Deps:
    """Real dependencies by default. Tests may pass stand-ins (clearly test-only)."""
    def __init__(self, builder=None, memory=None):
        if builder is None:
            from . import builder as builder
        if memory is None:
            from . import memory as memory
        self.builder, self.memory = builder, memory


def process_job(job_id: str, deps: Deps | None = None, opted_in_to_sharing: bool = True) -> dict:
    deps = deps or Deps()
    job = store.update_job(job_id, status="running")
    ws, task = job["workspace"], job["request"]
    try:
        # 1. Retrieve memory
        recalled = asyncio.run(deps.memory.recall(ws, "How must carrier delivery confirmations be matched to shipments?"))
        store.log_step(job_id, "memory_retrieved", recalled)

        # 2. Construct
        wf = deps.builder.construct(task, recalled)
        store.append(job_id, "versions", {"version": 1, "workflow": wf, "why": "initial construction"})
        store.log_step(job_id, "constructed", {"version": 1})

        # 3. Shared lesson from the other workspace (opt-in, verified, tested locally)
        cases = list(FRESH_TESTS_A)
        imported = shared.import_into(shared.build_artifact_from_b(), OPERATION, opted_in_to_sharing)
        store.log_step(job_id, "shared_lesson", {k: v for k, v in imported.items() if k != "test_case"})
        lessons = list(recalled)
        if imported["accepted"]:
            cases.append(imported["test_case"])
            lessons.append(imported["lesson"]["invariant"] + " Fix pattern: " + imported["lesson"]["fix_pattern"])

        # 4. Test -> repair loop
        version = 1
        for attempt in range(MAX_REPAIRS + 1):
            results = []
            for c in cases:
                shipments = c.get("shipments", SHIPMENTS_A)
                results.append(tester.run_case(wf, shipments, c))
            store.append(job_id, "tests", {"version": version, "results": results})
            failures = [r for r in results if not r["passed"]]
            store.log_step(job_id, "tested", {"version": version, "passed": len(results) - len(failures), "failed": len(failures)})
            if not failures or attempt == MAX_REPAIRS:
                break
            wf = deps.builder.repair(task, wf, failures, lessons)
            version += 1
            store.append(job_id, "versions", {"version": version, "workflow": wf,
                                              "why": "repair after: " + ", ".join(f["name"] for f in failures)})
            store.log_step(job_id, "repaired", {"version": version})

        ready = not failures
        if ready:
            asyncio.run(deps.memory.remember(ws, f"Workflow v{version} for '{task}' passed {len(results)} independent tests.",
                                             "verified_outcome", f"job:{job_id}"))
        report = {
            "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
            "final_version": version,
            "ready_for_review": ready,
            "summary": (f"Version {version} passed all {len(results)} independent tests and awaits your approval."
                        if ready else f"Version {version} still fails {len(failures)} test(s). Not ready; needs a human."),
            "repairs": version - 1,
            "shared_lesson_used": imported["accepted"],
            "needs_human": [] if ready else [f["name"] for f in failures],
        }
        store.update_job(job_id, status="awaiting_approval" if ready else "failed", report=report)
        return report
    except Exception as e:  # recorded honestly, never hidden
        store.log_step(job_id, "error", repr(e))
        store.update_job(job_id, status="error", report={"summary": f"Error: {e!r}", "ready_for_review": False})
        raise


def run_due_jobs(deps: Deps | None = None) -> list[str]:
    store.recover_interrupted()
    done = []
    for j in store.list_jobs():
        if j["status"] == "queued" and j["run_at"] <= time.time():
            process_job(j["id"], deps)
            done.append(j["id"])
    return done


async def seed_memory(memory=None) -> None:
    from .data import CONFIRMED_RULES_A
    memory = memory or Deps().memory
    for rule in CONFIRMED_RULES_A:
        await memory.remember("bayline", rule, "confirmed_rule", "ops-manager confirmation")
