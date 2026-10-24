from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from chromadb import PersistentClient
from chromadb.utils import embedding_functions

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "golden_it_support_tickets.csv"
COLLECTION_NAME = "golden_it_support_tickets"
CHROMA_PATH = ROOT_DIR / ".chroma"


def _load_ticket_rows() -> list[dict[str, Any]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    rows: list[dict[str, Any]] = []

    for record in df.to_dict(orient="records"):
        initial = str(record.get("initial_message") or "").strip()
        resolution = str(record.get("resolution_summary") or "").strip()
        rows.append(
            {
                "ticket_id": str(record.get("ticket_id") or "unknown"),
                "initial_message": initial,
                "resolution_summary": resolution,
                "product_area": str(record.get("product_area") or ""),
                "issue_type": str(record.get("issue_type") or ""),
                "priority": str(record.get("priority") or ""),
                "channel": str(record.get("channel") or ""),
                "platform": str(record.get("platform") or ""),
                "region": str(record.get("region") or ""),
                "scenario_key": str(record.get("scenario_key") or ""),
                "combined_text": " ".join(part for part in [initial, resolution] if part),
            }
        )

    return rows


def build_knowledge_base(force_rebuild: bool = True) -> Any:
    """Create and populate a Chroma collection from the golden ticket dataset."""
    client = PersistentClient(path=str(CHROMA_PATH))
    embedder = embedding_functions.DefaultEmbeddingFunction()

    if force_rebuild:
        try:
            client.delete_collection(name=COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedder,
    )

    rows = _load_ticket_rows()
    if collection.count() == 0 or force_rebuild:
        collection.add(
            documents=[row["combined_text"] for row in rows],
            metadatas=[
                {
                    "ticket_id": row["ticket_id"],
                    "product_area": row["product_area"],
                    "issue_type": row["issue_type"],
                    "priority": row["priority"],
                    "channel": row["channel"],
                    "platform": row["platform"],
                    "region": row["region"],
                    "scenario_key": row["scenario_key"],
                }
                for row in rows
            ],
            ids=[row["ticket_id"] for row in rows],
        )

    return collection


def find_relevant_tickets(question: str, limit: int = 5) -> list[dict[str, Any]]:
    """Query the ticket dataset and return the closest matches."""
    collection = build_knowledge_base(force_rebuild=False)
    results = collection.query(query_texts=[question], n_results=limit)

    matches: list[dict[str, Any]] = []
    for i in range(len(results.get("ids", [[]])[0])):
        ticket_id = results["ids"][0][i]
        metadata = results["metadatas"][0][i]
        document = results["documents"][0][i]
        matches.append(
            {
                "ticket_id": ticket_id,
                "product_area": metadata.get("product_area", ""),
                "issue_type": metadata.get("issue_type", ""),
                "priority": metadata.get("priority", ""),
                "channel": metadata.get("channel", ""),
                "platform": metadata.get("platform", ""),
                "region": metadata.get("region", ""),
                "scenario_key": metadata.get("scenario_key", ""),
                "match_text": document,
            }
        )
    return matches


if __name__ == "__main__":
    build_knowledge_base(force_rebuild=True)

    sample_questions = [
        "I can't log in because my password is incorrect.",
        "My email is flaky and I cannot access the app.",
        "The analytics dashboard keeps crashing.",
        "How do I export my data from the dashboard?",
        "The billing page is very slow and takes a long time to load.",
    ]

    for question in sample_questions:
        print(f"\nQuestion: {question}")
        for result in find_relevant_tickets(question, limit=3):
            print(
                "- ticket_id=%s | issue_type=%s | priority=%s | match=%s"
                % (
                    result["ticket_id"],
                    result["issue_type"],
                    result["priority"],
                    result["match_text"][:140],
                )
            )
