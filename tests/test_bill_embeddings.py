import pytest

from bill_analysis import load_bill_data
from bill_embeddings import (
    build_bill_documents,
    cosine_similarity,
    semantic_search_bills,
)


def test_build_bill_documents_includes_searchable_bill_facts():
    data = load_bill_data("data/bills.json")

    documents = build_bill_documents(data["bills"])

    pse = next(document for document in documents if document["bill_id"] == "pse_electricity")
    assert "PSE Electricity" in pse["text"]
    assert "Category: utilities" in pse["text"]
    assert "Amount due: $142.50" in pse["text"]


def test_cosine_similarity_orders_related_vectors():
    assert cosine_similarity([1.0, 0.0], [0.9, 0.1]) > cosine_similarity(
        [1.0, 0.0],
        [0.0, 1.0],
    )


def test_semantic_search_ranks_the_expected_bill():
    def fake_embedder(texts, model=None, base_url=None):
        vectors = [[1.0, 0.0]]
        for text in texts[1:]:
            if "PSE Electricity" in text:
                vectors.append([0.95, 0.05])
            else:
                vectors.append([0.0, 1.0])
        return vectors

    results = semantic_search_bills(
        "Find my power bill",
        embedder=fake_embedder,
    )

    assert results[0]["bill_id"] == "pse_electricity"
    assert results[0]["score"] == pytest.approx(0.9986, abs=0.0001)


def test_cosine_similarity_rejects_mismatched_dimensions():
    with pytest.raises(ValueError, match="same dimensions"):
        cosine_similarity([1.0], [1.0, 2.0])
