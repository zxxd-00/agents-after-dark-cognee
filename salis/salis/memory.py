"""Cognee business memory. Provenance and authority stay in Salis (the ledger in
store.py): Cognee stores and retrieves text; it never decides what is confirmed
and it never authorizes execution. Each workspace is its own Cognee dataset."""

from . import store

CATEGORIES = {"observed_fact", "ai_inference", "confirmed_rule", "verified_outcome", "invalidated"}


def _dataset(workspace: str) -> str:
    return f"salis_ws_{workspace}"


async def remember(workspace: str, text: str, category: str, source: str) -> None:
    if category not in CATEGORIES:
        raise ValueError(f"unknown memory category {category}")
    import cognee
    tagged = f"[{category}] {text}"
    await cognee.remember(tagged, dataset_name=_dataset(workspace))
    store.record_memory({"workspace": workspace, "category": category, "text": text, "source": source})


async def recall(workspace: str, query: str) -> list[str]:
    import cognee
    results = await cognee.recall(query, datasets=[_dataset(workspace)])
    return [str(r) for r in (results or [])]
