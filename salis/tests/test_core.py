"""Offline tests for the deterministic parts. The builder/memory stand-ins below are
TEST-ONLY; the app always uses the real model and real Cognee."""

import copy
import os
import tempfile

os.environ["SALIS_STATE"] = os.path.join(tempfile.mkdtemp(), "state.json")

from salis import nightshift, shared, store, tester, workflow  # noqa: E402
from salis.data import FRESH_TESTS_A, SHIPMENTS_A  # noqa: E402

BY_NAME = {"match_by": "customer_name", "rules": [], "default_action": "mark_delivered"}
BY_ID = {"match_by": "shipment_id", "rules": [], "default_action": "mark_delivered"}
BY_ID_SAFE = {"match_by": "shipment_id", "default_action": "mark_delivered",
              "rules": [{"when": {"field": "status", "equals": "cancelled"}, "action": "flag_exception"}]}


def test_rejects_unsupported_ops():
    for bad in [{"match_by": "email", "default_action": "skip"},
                {"match_by": "shipment_id", "default_action": "delete_everything"},
                {"match_by": "shipment_id", "default_action": "skip",
                 "rules": [{"when": {"field": "status", "equals": "x"}, "action": "run_code"}]}]:
        try:
            workflow.validate(bad)
            assert False, "should have rejected"
        except workflow.InvalidWorkflow:
            pass


def test_name_matching_fails_hard_case_and_id_matching_passes():
    hard = FRESH_TESTS_A[1]
    assert not tester.run_case(BY_NAME, SHIPMENTS_A, hard)["passed"]
    assert tester.run_case(BY_ID, SHIPMENTS_A, hard)["passed"]


def test_all_local_fresh_tests_pass_for_id_matching():
    assert all(r["passed"] for r in tester.run_suite(BY_ID, SHIPMENTS_A, FRESH_TESTS_A))


def test_executor_never_mutates_source():
    before = copy.deepcopy(SHIPMENTS_A)
    workflow.execute(BY_ID, SHIPMENTS_A, FRESH_TESTS_A[0]["updates"])
    assert SHIPMENTS_A == before


def test_shared_artifact_is_sanitized_and_tamper_checked():
    art = shared.build_artifact_from_b()
    assert shared.sanitization_problems(art) == []
    assert shared.import_into(art, nightshift.OPERATION, opted_in=True)["accepted"]
    assert not shared.import_into(art, nightshift.OPERATION, opted_in=False)["accepted"]
    assert not shared.import_into(art, "invoice_processing", opted_in=True)["accepted"]
    tampered = copy.deepcopy(art)
    tampered["body"]["invariant"] = "anything goes"
    assert not shared.import_into(tampered, nightshift.OPERATION, opted_in=True)["accepted"]
    leaky = copy.deepcopy(art)
    leaky["body"]["limitations"] = "seen at RW-77310"
    leaky["signature"] = shared._sign(leaky["body"])
    assert not shared.import_into(leaky, nightshift.OPERATION, opted_in=True)["accepted"]


def test_shared_lesson_catches_cancelled_case():
    case = shared.import_into(shared.build_artifact_from_b(), nightshift.OPERATION, True)["test_case"]
    assert not tester.run_case(BY_ID, case["shipments"], case)["passed"]
    assert tester.run_case(BY_ID_SAFE, case["shipments"], case)["passed"]


class _StubMemory:  # test-only
    async def recall(self, ws, q):
        return ["match by shipment ID"]

    async def remember(self, ws, text, cat, src):
        store.record_memory({"workspace": ws, "category": cat, "text": text, "source": src})


class _StubBuilder:  # test-only: v1 lacks the cancelled rule, repair adds it
    def construct(self, task, mem):
        return dict(BY_ID)

    def repair(self, task, wf, failures, lessons):
        return dict(BY_ID_SAFE)


class _BadBuilder(_StubBuilder):
    def repair(self, task, wf, failures, lessons):
        return dict(BY_NAME)


def test_night_shift_repairs_and_reports_from_records():
    job = store.create_job("match confirmations", "bayline")
    report = nightshift.process_job(job["id"], nightshift.Deps(_StubBuilder(), _StubMemory()))
    j = store.get_job(job["id"])
    assert report["ready_for_review"] and report["repairs"] == 1 and report["shared_lesson_used"]
    assert j["status"] == "awaiting_approval"
    assert [t["version"] for t in j["tests"]] == [1, 2]
    assert not all(r["passed"] for r in j["tests"][0]["results"])
    assert all(r["passed"] for r in j["tests"][1]["results"])


def test_failed_repair_is_reported_as_failure():
    job = store.create_job("match confirmations", "bayline")
    report = nightshift.process_job(job["id"], nightshift.Deps(_BadBuilder(), _StubMemory()))
    assert not report["ready_for_review"]
    assert store.get_job(job["id"])["status"] == "failed"


def test_interrupted_job_is_recovered():
    job = store.create_job("x", "bayline")
    store.update_job(job["id"], status="running")
    assert job["id"] in store.recover_interrupted()
    assert store.get_job(job["id"])["status"] == "queued"


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f()
        print("PASS", f.__name__)
    print(f"{len(fns)} passed")
