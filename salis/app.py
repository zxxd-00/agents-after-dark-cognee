"""Salis dashboard: assign a job, Run Now, morning report. All data comes from the job store."""

import asyncio
import json

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from salis import nightshift, store  # noqa: E402

st.set_page_config(page_title="Salis After Dark", layout="wide")
st.title("Salis After Dark")
st.caption("Workspace: Bayline Freight (synthetic data)")

with st.sidebar:
    st.subheader("Business memory")
    if st.button("Seed confirmed rule into Cognee"):
        asyncio.run(nightshift.seed_memory())
        st.success("Saved.")
    for m in store.memory_ledger("bayline"):
        st.markdown(f"**{m['category']}** — {m['text']}  \n_source: {m['source']}_")

st.subheader("Assign a job")
st.caption("Text input (fallback). This is not a phone call.")
req = st.text_input("Request", "Build an automation that matches carrier delivery confirmations to our shipments.")
c1, c2 = st.columns(2)
if c1.button("Queue for tonight"):
    store.create_job(req, "bayline", source="text", run_at=float("inf"))
    st.success("Queued for the night shift.")
if c2.button("Run Now (same code as the night shift)"):
    job = store.create_job(req, "bayline", source="text")
    with st.spinner("Night shift running..."):
        nightshift.process_job(job["id"])
    st.rerun()

st.divider()
st.subheader("Morning report")
for job in reversed(store.list_jobs()):
    r = job["report"] or {}
    with st.expander(f"[{job['status']}] {job['request'][:70]}  —  job {job['id']}", expanded=job is store.list_jobs()[-1]):
        if r:
            (st.success if r.get("ready_for_review") else st.error)(r.get("summary", ""))
        for step in job["steps"]:
            if step["step"] == "memory_retrieved":
                st.markdown("**Knowledge retrieved from Cognee**")
                for m in step["detail"]:
                    st.write("•", m)
            if step["step"] == "shared_lesson":
                st.markdown(f"**Shared lesson from another workspace:** accepted = {step['detail']['accepted']} ({step['detail']['reason']})")
        for v in job["versions"]:
            st.markdown(f"**Workflow v{v['version']}** — {v['why']}")
            st.code(json.dumps(v["workflow"], indent=2), language="json")
        for t in job["tests"]:
            st.markdown(f"**Independent tests on v{t['version']}**")
            st.table([{"test": x["name"], "source": x.get("source", "local"),
                       "result": "PASS" if x["passed"] else "FAIL", "problems": "; ".join(x["problems"])}
                      for x in t["results"]])
        if job["status"] == "awaiting_approval":
            if st.button("Approve this version", key=f"ok-{job['id']}"):
                store.record_approval(job["id"], r["final_version"], "approved")
                store.update_job(job["id"], status="approved")
                st.rerun()
