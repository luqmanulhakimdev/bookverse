from ..schemas import Book
from .base import HttpProvider


class OpenLibraryProvider(HttpProvider):
    name = "open_library"

    async def search(self, query: str, page: int, limit: int) -> list[Book]:
        data = await self.get_json(
            f"{self.base_url}/search.json",
            {"q": query, "page": page, "limit": limit},
        )
        docs = data.get("docs", [])
        if not isinstance(docs, list):
            return []
        books = []
        for doc in docs:
            if not isinstance(doc, dict) or not doc.get("key") or not doc.get("title"):
                continue
            cover_id = doc.get("cover_i")
            languages = doc.get("language")
            year = doc.get("first_publish_year")
            subjects = doc.get("subject", [])
            books.append(
                Book(
                    id=str(doc["key"]),
                    title=str(doc["title"]),
                    authors=[str(a) for a in doc.get("author_name", []) if isinstance(a, str)],
                    genres=[str(g) for g in subjects[:8] if isinstance(g, str)]
                    if isinstance(subjects, list)
                    else [],
                    language=languages[0] if isinstance(languages, list) and languages else None,
                    published_year=year if isinstance(year, int) else None,
                    cover_url=f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
                    if cover_id
                    else None,
                    source=self.name,
                    source_url=f"https://openlibrary.org{doc['key']}",
                    access_type="read" if doc.get("public_scan_b") else "metadata",
                    access_url=f"https://openlibrary.org{doc['key']}"
                    if doc.get("public_scan_b")
                    else None,
                )
            )
        return books
