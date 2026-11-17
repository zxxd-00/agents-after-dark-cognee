"""Durable job store (a JSON file). Every step is written to disk immediately,
so a job survives a crash and the morning report reads only real records."""

import json
import os
import threading
import time
import uuid
from pathlib import Path

STATE_PATH = Path(os.getenv("SALIS_STATE", ".salis/state.json"))
_lock = threading.Lock()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _load() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"jobs": [], "memory_ledger": [], "approvals": []}


def _save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_PATH)  # atomic: never leaves a half-written file


def create_job(request: str, workspace: str, source: str = "text", run_at: float | None = None) -> dict:
    job = {
        "id": uuid.uuid4().hex[:8],
        "request": request,
        "workspace": workspace,
        "source": source,  # "text" (fallback UI) or "phone" (only when a real call created it)
        "status": "queued",
        "created": _now(),
        "run_at": run_at or time.time(),
        "steps": [],
        "versions": [],
        "tests": [],
        "report": None,
    }
    with _lock:
        state = _load()
        state["jobs"].append(job)
        _save(state)
    return job


def update_job(job_id: str, **fields) -> dict:
    with _lock:
        state = _load()
        job = next(j for j in state["jobs"] if j["id"] == job_id)
        job.update(fields)
        _save(state)
        return job


def log_step(job_id: str, name: str, detail) -> None:
    with _lock:
        state = _load()
        job = next(j for j in state["jobs"] if j["id"] == job_id)
        job["steps"].append({"time": _now(), "step": name, "detail": detail})
        _save(state)


def append(job_id: str, key: str, item) -> None:
    with _lock:
        state = _load()
        job = next(j for j in state["jobs"] if j["id"] == job_id)
        job[key].append(item)
        _save(state)


def get_job(job_id: str) -> dict:
    return next(j for j in _load()["jobs"] if j["id"] == job_id)


def list_jobs() -> list[dict]:
    return _load()["jobs"]


def record_memory(entry: dict) -> None:
    with _lock:
        state = _load()
        state["memory_ledger"].append({"time": _now(), **entry})
        _save(state)


def memory_ledger(workspace: str) -> list[dict]:
    return [m for m in _load()["memory_ledger"] if m["workspace"] == workspace]


def record_approval(job_id: str, version: int, decision: str) -> None:
    with _lock:
        state = _load()
        state["approvals"].append({"time": _now(), "job": job_id, "version": version, "decision": decision})
        _save(state)


def recover_interrupted() -> list[str]:
    """Jobs left 'running' by a crash are re-queued (they have no external effects:
    all workflow runs happen on disposable copies of test data)."""
    with _lock:
        state = _load()
        ids = []
        for j in state["jobs"]:
            if j["status"] == "running":
                j["status"] = "queued"
                j["steps"].append({"time": _now(), "step": "recovered", "detail": "re-queued after interruption"})
                ids.append(j["id"])
        _save(state)
        return ids
