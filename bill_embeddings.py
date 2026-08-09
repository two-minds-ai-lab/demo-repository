import argparse
import json
import math
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bill_analysis import DEFAULT_DATA_FILE, load_bill_data


DEFAULT_EMBEDDING_MODEL = "qwen3-embedding:4b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
RETRIEVAL_INSTRUCTION = (
    "Given a bill-related search query, retrieve the most relevant bill records."
)


def build_bill_documents(bills):
    """Convert structured bills into searchable text documents."""
    documents = []
    for bill in bills:
        statement = bill["current_statement"]
        previous = bill.get("history", [])
        previous_amount = previous[0]["amount_due"] if previous else None
        text = (
            f"Bill name: {bill['name']}. "
            f"Bill ID: {bill['bill_id']}. "
            f"Category: {bill['category']}. "
            f"Frequency: {bill['recurrence']['frequency']}. "
            f"Current statement month: {statement['statement_month']}. "
            f"Amount due: ${statement['amount_due']:.2f}. "
            f"Due date: {statement['due_date']}. "
            f"Status: {statement['status']}."
        )
        if previous_amount is not None:
            text += f" Previous-month amount: ${previous_amount:.2f}."

        documents.append(
            {
                "bill_id": bill["bill_id"],
                "name": bill["name"],
                "category": bill["category"],
                "text": text,
            }
        )
    return documents


def embed_texts(
    texts,
    model=None,
    base_url=None,
    timeout=180,
):
    """Generate embeddings with a local Ollama embedding model."""
    model = model or os.environ.get(
        "BILL_EMBEDDING_MODEL",
        DEFAULT_EMBEDDING_MODEL,
    )
    base_url = (
        base_url
        or os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
    ).rstrip("/")
    request = Request(
        f"{base_url}/api/embed",
        data=json.dumps({"model": model, "input": texts}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ollama embedding request failed with HTTP {error.code}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(
            f"Cannot reach Ollama at {base_url}. Start Ollama and try again."
        ) from error

    embeddings = payload.get("embeddings")
    if not embeddings or len(embeddings) != len(texts):
        raise RuntimeError("Ollama returned an invalid embedding response.")
    return embeddings


def cosine_similarity(left, right):
    """Return cosine similarity for two equal-length vectors."""
    if len(left) != len(right):
        raise ValueError("Embedding vectors must have the same dimensions.")

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0

    dot_product = sum(
        left_value * right_value
        for left_value, right_value in zip(left, right)
    )
    return dot_product / (left_norm * right_norm)


def semantic_search_bills(
    query,
    data_file=DEFAULT_DATA_FILE,
    limit=3,
    model=None,
    base_url=None,
    embedder=embed_texts,
):
    """Rank bills by semantic similarity to a natural-language query."""
    data = load_bill_data(Path(data_file))
    documents = build_bill_documents(data["bills"])
    query_text = f"Instruct: {RETRIEVAL_INSTRUCTION}\nQuery: {query}"
    vectors = embedder(
        [query_text, *(document["text"] for document in documents)],
        model=model,
        base_url=base_url,
    )
    query_vector = vectors[0]

    results = []
    for document, vector in zip(documents, vectors[1:]):
        results.append(
            {
                "bill_id": document["bill_id"],
                "name": document["name"],
                "category": document["category"],
                "score": cosine_similarity(query_vector, vector),
                "evidence": document["text"],
            }
        )

    results.sort(key=lambda result: result["score"], reverse=True)
    return results[:limit]


def main():
    parser = argparse.ArgumentParser(
        description="Search the sample bills with local Qwen3 embeddings."
    )
    parser.add_argument("query", nargs="+", help="Natural-language bill query.")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument(
        "--model",
        default=os.environ.get(
            "BILL_EMBEDDING_MODEL",
            DEFAULT_EMBEDDING_MODEL,
        ),
    )
    args = parser.parse_args()

    query = " ".join(args.query)
    results = semantic_search_bills(
        query,
        limit=args.limit,
        model=args.model,
    )
    print(f"SEMANTIC BILL SEARCH\nQuery: {query}\n")
    for index, result in enumerate(results, start=1):
        print(
            f"{index}. {result['name']} "
            f"(score: {result['score']:.4f}, category: {result['category']})"
        )


if __name__ == "__main__":
    main()
