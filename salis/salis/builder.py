"""Workflow builder: real model reasoning. The model proposes JSON; Salis validates it.
Nothing here imports the tester or sees fresh test cases."""

import json
import os

from . import workflow
from .data import CONSTRUCTION_EXAMPLES

MODEL = os.getenv("SALIS_MODEL", "gpt-4o-mini")


def _client():
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"))


def _ask(prompt: str) -> dict:
    resp = _client().chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You design workflows for a logistics automation engine. "
             "Reply with ONLY a JSON object matching the schema. Use only the operations the schema allows."},
            {"role": "user", "content": prompt},
        ],
    )
    return json.loads(resp.choices[0].message.content)


def construct(task: str, memory_context: list[str]) -> dict:
    prompt = (
        f"TASK: {task}\n\nWORKFLOW SCHEMA:\n{workflow.SCHEMA_DOC}\n\n"
        f"EXAMPLES OF CORRECT BEHAVIOR:\n{json.dumps(CONSTRUCTION_EXAMPLES, indent=1)}\n\n"
        f"BUSINESS MEMORY (context, may be incomplete):\n" + "\n".join(f"- {m}" for m in memory_context)
    )
    return workflow.validate(_ask(prompt))


def repair(task: str, current: dict, failures: list[dict], lessons: list[str]) -> dict:
    prompt = (
        f"TASK: {task}\n\nWORKFLOW SCHEMA:\n{workflow.SCHEMA_DOC}\n\n"
        f"CURRENT WORKFLOW:\n{json.dumps(current, indent=1)}\n\n"
        f"FAILED INDEPENDENT TESTS:\n{json.dumps([{k: f[k] for k in ('name', 'problems')} for f in failures], indent=1)}\n\n"
        f"RELEVANT LESSONS:\n" + "\n".join(f"- {l}" for l in lessons) +
        "\n\nPropose a corrected workflow."
    )
    return workflow.validate(_ask(prompt))
