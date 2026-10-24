from dotenv import load_dotenv
import os
from langchain_chroma import Chroma
from langchain_community.document_loaders import JSONLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveJsonSplitter
from langchain_community.retrievers import BM25Retriever
from langchain_core.retrievers import EnsembleRetriever
from langchain_core.documents import Document
import json


load_dotenv()
vector_store = None
_retriever = None

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_PATH,"data","golden_it_support_tickets.json")
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

def _load_docs() -> list[Document]:
    with open(DATA_DIR, "r") as f:
        data = json.load(f)

    docs = []
    for ticket in data:
        # Searchable content for BM25 + vector retrieval
        content = (
            f"Issue: {ticket.get('initial_message', '')}\n"
            f"Product Area: {ticket.get('product_area', '')}\n"
            f"Issue Type: {ticket.get('issue_type', '')}\n"
            f"Resolution: {ticket.get('resolution_summary', '')}"
        )
        docs.append(Document(
            page_content=content,
            metadata={
                "ticket_id":           ticket.get("ticket_id", ""),
                "created_at":          ticket.get("created_at", ""),
                "customer_id":         ticket.get("customer_id", ""),
                "customer_segment":    ticket.get("customer_segment", ""),
                "channel":             ticket.get("channel", ""),
                "product_area":        ticket.get("product_area", ""),
                "issue_type":          ticket.get("issue_type", ""),
                "priority":            ticket.get("priority", ""),
                "status":              ticket.get("status", ""),
                "sla_plan":            ticket.get("sla_plan", ""),
                "resolution_time_hours": ticket.get("resolution_time_hours"),
                "reopened":            ticket.get("reopened", False),
                "customer_sentiment":  ticket.get("customer_sentiment", ""),
                "csat_score":          ticket.get("csat_score"),
                "has_attachment":      ticket.get("has_attachment", False),
                "platform":            ticket.get("platform", ""),
                "region":              ticket.get("region", ""),
                "scenario_key":        ticket.get("scenario_key", ""),
            }
        ))
    return docs

def ingest():
    document = _load_docs()
    splitter = RecursiveJsonSplitter(
        chunk_size = 500
    )
    chunks = splitter.split_documents(document)
    global vector_store
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory="chroma_db"
    )
def load_vector_store():
    global vector_store, _retriever
    vector_store = Chroma(
        persist_directory="chroma_db",
        embedding_function=get_embeddings()
        )
    print("✅ Vector store loaded from disk")
    docs = _load_docs()

    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k = 3

    vector_retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )

    # 3. Build ensemble once — reused for every query
    _retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[0.4, 0.6]
    )
    print("✅ Hybrid retriever ready")
def retrieve_relevant_chunks(query: str, k: int = 3):
    if _retriever is None:
        raise RuntimeError("Retriever not initialized. Call load_vector_store() at startup.")

    results = _retriever.invoke(query)

    if not results:
        raise ValueError("Could not retrieve relevant chunks")

    return [doc.page_content for doc in results[:k]]

def _load_store() -> dict[str, dict]:
    with open(DATA_DIR, "r") as f:
        data = json.load(f)
    return {ticket["ticket_id"]: ticket for ticket in data}


def _save_store(store: dict[str, dict]):
    with open(DATA_DIR, "w") as f:
        json.dump(list(store.values()), f, indent=2)


if __name__ == '__main__':
    ingest()
    