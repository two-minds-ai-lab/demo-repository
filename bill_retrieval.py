import argparse
import re
import sqlite3
from decimal import Decimal

from bill_analysis import DEFAULT_DATA_FILE, load_bill_data
from bill_embeddings import build_bill_documents, semantic_search_bills


QUERY_STOPWORDS = {
    "a",
    "all",
    "amount",
    "at",
    "bill",
    "bills",
    "find",
    "for",
    "has",
    "is",
    "latest",
    "me",
    "my",
    "of",
    "on",
    "please",
    "show",
    "statement",
    "the",
    "was",
    "which",
    "with",
}
AMOUNT_PATTERN = re.compile(r"(?<![\d.])\d+\.\d{2}(?![\d.])")
DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _fts_query(query):
    tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9]+", query)
        if token.lower() not in QUERY_STOPWORDS
    ]
    if not tokens:
        return None
    return " OR ".join(f'"{token}"' for token in tokens)


def _money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _structured_bill_ids(query, bills):
    """Return exact matches for amounts or ISO dates present in a query."""
    requested_amounts = {
        Decimal(value).quantize(Decimal("0.01"))
        for value in AMOUNT_PATTERN.findall(query)
    }
    requested_dates = set(DATE_PATTERN.findall(query))
    if not requested_amounts and not requested_dates:
        return None

    matching_ids = set()
    for bill in bills:
        statements = [
            bill["current_statement"],
            *bill.get("history", []),
        ]
        amount_match = not requested_amounts or any(
            _money(statement["amount_due"]) in requested_amounts
            for statement in statements
        )
        date_match = not requested_dates or any(
            statement.get("due_date") in requested_dates
            for statement in statements
        )
        if amount_match and date_match:
            matching_ids.add(bill["bill_id"])
    return matching_ids


def term_search_bills(query, data_file=DEFAULT_DATA_FILE, limit=6):
    """Rank bills with an in-memory SQLite FTS5/BM25 index."""
    data = load_bill_data(data_file)
    structured_ids = _structured_bill_ids(query, data["bills"])
    if structured_ids == set():
        return []

    documents = build_bill_documents(data["bills"])
    if structured_ids is not None:
        documents = [
            document
            for document in documents
            if document["bill_id"] in structured_ids
        ]

    text_query = AMOUNT_PATTERN.sub(" ", DATE_PATTERN.sub(" ", query))
    fts_query = _fts_query(text_query)
    if not fts_query:
        return [
            {
                "bill_id": document["bill_id"],
                "name": document["name"],
                "category": document["category"],
                "evidence": document["text"],
                "score": 0.0,
                "match_type": "exact structured match",
            }
            for document in documents[:limit]
        ]

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            """
            CREATE VIRTUAL TABLE bill_documents USING fts5(
                bill_id UNINDEXED,
                name,
                category,
                text
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO bill_documents (bill_id, name, category, text)
            VALUES (:bill_id, :name, :category, :text)
            """,
            documents,
        )
        rows = connection.execute(
            """
            SELECT bill_id, name, category, text, bm25(bill_documents) AS score
            FROM bill_documents
            WHERE bill_documents MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
    finally:
        connection.close()

    return [
        {
            "bill_id": bill_id,
            "name": name,
            "category": category,
            "score": score,
            "evidence": evidence,
            "match_type": "bm25",
        }
        for bill_id, name, category, evidence, score in rows
    ]


def reciprocal_rank_fusion(result_sets, rank_constant=60, limit=3):
    """Combine ranked result sets without comparing their raw score scales."""
    fused = {}
    for source, results in result_sets.items():
        for rank, result in enumerate(results, start=1):
            bill_id = result["bill_id"]
            entry = fused.setdefault(
                bill_id,
                {
                    "bill_id": bill_id,
                    "name": result["name"],
                    "category": result["category"],
                    "evidence": result["evidence"],
                    "score": 0.0,
                    "ranks": {},
                },
            )
            entry["score"] += 1 / (rank_constant + rank)
            entry["ranks"][source] = rank

    ranked = sorted(
        fused.values(),
        key=lambda result: (-result["score"], result["name"]),
    )
    return ranked[:limit]


def hybrid_search_bills(
    query,
    data_file=DEFAULT_DATA_FILE,
    limit=3,
    model=None,
    base_url=None,
    embedder=None,
):
    """Combine BM25 and semantic bill rankings with rank fusion."""
    candidate_limit = max(limit * 2, 6)
    term_results = term_search_bills(
        query,
        data_file=data_file,
        limit=candidate_limit,
    )
    data = load_bill_data(data_file)
    if _structured_bill_ids(query, data["bills"]) is not None:
        return reciprocal_rank_fusion(
            {"bm25": term_results},
            limit=limit,
        )

    semantic_kwargs = {
        "query": query,
        "data_file": data_file,
        "limit": candidate_limit,
        "model": model,
        "base_url": base_url,
    }
    if embedder is not None:
        semantic_kwargs["embedder"] = embedder
    semantic_results = semantic_search_bills(**semantic_kwargs)

    return reciprocal_rank_fusion(
        {
            "bm25": term_results,
            "semantic": semantic_results,
        },
        limit=limit,
    )


def search_bills(query, mode="hybrid", **kwargs):
    """Search bills using bm25, semantic, or hybrid retrieval."""
    if mode == "bm25":
        allowed = {"data_file", "limit"}
        return term_search_bills(
            query,
            **{key: value for key, value in kwargs.items() if key in allowed},
        )
    if mode == "semantic":
        return semantic_search_bills(query, **kwargs)
    if mode == "hybrid":
        return hybrid_search_bills(query, **kwargs)
    raise ValueError("Retrieval mode must be bm25, semantic, or hybrid.")


def main():
    parser = argparse.ArgumentParser(
        description="Compare BM25, semantic, and hybrid bill retrieval."
    )
    parser.add_argument("query", nargs="+", help="Natural-language bill query.")
    parser.add_argument(
        "--mode",
        choices=("bm25", "semantic", "hybrid"),
        default="hybrid",
    )
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    query = " ".join(args.query)
    results = search_bills(query, mode=args.mode, limit=args.limit)
    print(f"{args.mode.upper()} BILL SEARCH\nQuery: {query}\n")
    for index, result in enumerate(results, start=1):
        ranks = result.get("ranks")
        rank_text = f", ranks: {ranks}" if ranks else ""
        match_type = result.get("match_type")
        if match_type == "exact structured match":
            score_text = match_type
        else:
            score_text = f"score: {result['score']:.4f}"
        print(
            f"{index}. {result['name']} "
            f"({score_text}{rank_text})"
        )
    if not results:
        print("No matching bills found.")


if __name__ == "__main__":
    main()
