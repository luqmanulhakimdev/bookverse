import re
from collections.abc import Iterable

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)


def _names(value, relation: str) -> set[str]:
    names = set()
    for item in value or []:
        if isinstance(item, str) and item.strip():
            names.add(item.casefold().strip())
            continue
        name = getattr(getattr(item, relation, None), "name", None) or getattr(item, "name", None)
        if isinstance(name, str) and name.strip():
            names.add(name.casefold().strip())
    return names


def _tokens(text: str | None) -> set[str]:
    return {
        token
        for token in TOKEN_RE.findall((text or "").casefold())
        if len(token) > 2 and token not in STOP_WORDS
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left and right else 0.0


def book_similarity(target, candidate) -> tuple[float, list[str]]:
    """Return a stable 0..1 similarity and explanations for supported feature matches."""
    target_genres = _names(target.genres, "genre")
    candidate_genres = _names(candidate.genres, "genre")
    target_authors = _names(target.authors, "author")
    candidate_authors = _names(candidate.authors, "author")
    target_tokens = _tokens(f"{target.title} {target.description or ''}")
    candidate_tokens = _tokens(f"{candidate.title} {candidate.description or ''}")
    weights, values, reasons = [], [], []
    if target_genres and candidate_genres:
        weight, score = 0.45, _jaccard(target_genres, candidate_genres)
        weights.append(weight)
        values.append(score)
        shared = sorted(target_genres & candidate_genres)
        if shared:
            reasons.append("Shares genre: " + ", ".join(name.title() for name in shared[:3]))
    if target_authors and candidate_authors:
        weight, score = 0.30, _jaccard(target_authors, candidate_authors)
        weights.append(weight)
        values.append(score)
        shared = sorted(target_authors & candidate_authors)
        if shared:
            reasons.append("Also by " + ", ".join(name.title() for name in shared[:2]))
    if target_tokens and candidate_tokens:
        weights.append(0.20)
        values.append(_jaccard(target_tokens, candidate_tokens))
        if target_tokens & candidate_tokens:
            reasons.append("Similar title or description")
    target_language = (target.language or "").casefold()
    candidate_language = (candidate.language or "").casefold()
    if target_language and candidate_language:
        weights.append(0.05)
        values.append(float(target_language == candidate_language))
        if target_language == candidate_language:
            reasons.append("Same language")
    score = (
        sum(w * v for w, v in zip(weights, values, strict=True)) / sum(weights) if weights else 0
    )
    return round(score, 4), reasons


def recommend_books(candidates: Iterable, seeds: Iterable, excluded_ids: set[str], limit: int = 20):
    ranked = []
    seed_list = list(seeds)
    for book in candidates:
        if str(book.id) in excluded_ids:
            continue
        best_score, best_reasons, best_seed = 0.0, [], None
        for seed in seed_list:
            seed_book = getattr(seed, "book", seed)
            score, reasons = book_similarity(seed_book, book)
            rating = getattr(seed, "rating", None)
            preference = 1 + ((rating - 3) * 0.04 if isinstance(rating, int) else 0)
            adjusted = min(score * preference, 1.0)
            if adjusted > best_score:
                best_score, best_reasons, best_seed = adjusted, reasons, seed_book
        if best_score >= 0.1:
            if best_seed is not None and not best_reasons:
                best_reasons = [f"Similar to {best_seed.title}"]
            ranked.append(
                (best_score, str(book.title).casefold(), str(book.id), book, best_reasons)
            )
    ranked.sort(key=lambda row: (-row[0], row[1], row[2]))
    return [
        {"book": row[3], "score": round(row[0], 4), "reasons": row[4]} for row in ranked[:limit]
    ]
