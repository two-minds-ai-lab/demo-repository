import pytest

from bill_retrieval import (
    hybrid_search_bills,
    reciprocal_rank_fusion,
    search_bills,
    term_search_bills,
)


def test_bm25_ranks_exact_bill_name_first():
    results = term_search_bills("Chase Visa")

    assert results[0]["bill_id"] == "chase_visa"


def test_bm25_ranks_exact_amount_first():
    results = term_search_bills("Which bill is 142.50?")

    assert results[0]["bill_id"] == "pse_electricity"
    assert results[0]["match_type"] == "exact structured match"


def test_bm25_does_not_partially_match_a_different_amount():
    assert term_search_bills("142.40") == []


def test_bm25_matches_an_exact_due_date():
    results = term_search_bills("2026-08-10")

    assert [result["bill_id"] for result in results] == ["citi_mastercard"]


def test_reciprocal_rank_fusion_combines_independent_rankings():
    chase = {
        "bill_id": "chase_visa",
        "name": "Chase Visa",
        "category": "credit_card",
        "evidence": "Chase",
    }
    pse = {
        "bill_id": "pse_electricity",
        "name": "PSE Electricity",
        "category": "utilities",
        "evidence": "PSE",
    }

    results = reciprocal_rank_fusion(
        {
            "bm25": [chase, pse],
            "semantic": [pse, chase],
        }
    )

    assert {result["bill_id"] for result in results[:2]} == {
        "chase_visa",
        "pse_electricity",
    }
    assert results[0]["score"] == pytest.approx(results[1]["score"])


def test_hybrid_search_uses_semantics_when_terms_do_not_match():
    def fake_embedder(texts, model=None, base_url=None):
        vectors = [[1.0, 0.0]]
        for text in texts[1:]:
            if "PSE Electricity" in text:
                vectors.append([0.95, 0.05])
            else:
                vectors.append([0.0, 1.0])
        return vectors

    results = hybrid_search_bills(
        "Find my power bill",
        embedder=fake_embedder,
    )

    assert results[0]["bill_id"] == "pse_electricity"
    assert results[0]["ranks"]["semantic"] == 1


def test_hybrid_does_not_semantically_approximate_an_exact_amount():
    def unexpected_embedder(texts, model=None, base_url=None):
        raise AssertionError("Embedding search should not run for an exact amount.")

    assert hybrid_search_bills(
        "Find the bill for 142.40",
        embedder=unexpected_embedder,
    ) == []


def test_search_rejects_unknown_mode():
    with pytest.raises(ValueError, match="bm25, semantic, or hybrid"):
        search_bills("PSE", mode="unknown")
