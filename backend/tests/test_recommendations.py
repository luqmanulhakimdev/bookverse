from dataclasses import dataclass, field

from bookverse.recommendations import book_similarity, recommend_books


@dataclass
class FeatureBook:
    id: str
    title: str
    authors: list = field(default_factory=list)
    genres: list = field(default_factory=list)
    language: str | None = "en"
    description: str | None = None
    rating: int | None = None


def test_content_score_is_deterministic_and_explained():
    seed = FeatureBook(
        "1",
        "Sea Stories",
        ["Ursula Le Guin"],
        ["Fantasy"],
        description="A woman sails beyond the islands",
    )
    candidate = FeatureBook(
        "2", "The Far Shore", ["Ursula Le Guin"], ["Fantasy"], description="An island voyage"
    )
    score, reasons = book_similarity(seed, candidate)
    assert score == 0.8
    assert "Shares genre: Fantasy" in reasons
    assert "Also by Ursula Le Guin" in reasons
    assert "Same language" in reasons


def test_recommendations_exclude_current_and_rank_stably():
    seed = FeatureBook("1", "Ocean Tales", ["A. Author"], ["Fantasy"])
    same_author = FeatureBook("2", "Island Voyage", ["A. Author"], ["Fantasy"])
    unrelated = FeatureBook("3", "Car Repair", ["B. Mechanic"], ["Reference"])
    results = recommend_books([unrelated, same_author, seed], [seed], {"1"})
    assert [item["book"].id for item in results] == ["2"]
    assert results[0]["score"] > 0


def test_missing_metadata_has_no_invented_similarity():
    unknown_a = FeatureBook("a", "", authors=[], genres=[], language=None)
    unknown_b = FeatureBook("b", "", authors=[], genres=[], language=None)
    assert book_similarity(unknown_a, unknown_b) == (0, [])
