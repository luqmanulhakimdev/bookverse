from ..schemas import Book
from .base import HttpProvider


class GoogleBooksProvider(HttpProvider):
    name = "google_books"

    async def search(self, query: str, page: int, limit: int) -> list[Book]:
        data = await self.get_json(
            f"{self.base_url}/volumes",
            {"q": query, "startIndex": (page - 1) * limit, "maxResults": min(limit, 40)},
        )
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
        books = []
        for item in items:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            info = item.get("volumeInfo") or {}
            if not isinstance(info, dict) or not info.get("title"):
                continue
            links = info.get("imageLinks") or {}
            year_text = info.get("publishedDate", "")
            try:
                year = int(year_text[:4]) if len(year_text) >= 4 else None
            except (ValueError, TypeError):
                year = None
            access = item.get("accessInfo") or {}
            view = access.get("viewability")
            access_type = "preview" if view in {"PARTIAL", "FULL"} else "metadata"
            preview = access.get("webReaderLink") or info.get("previewLink")
            books.append(
                Book(
                    id=str(item["id"]),
                    title=str(info["title"]),
                    authors=[str(a) for a in info.get("authors", []) if isinstance(a, str)],
                    description=info.get("description")
                    if isinstance(info.get("description"), str)
                    else None,
                    language=info.get("language")
                    if isinstance(info.get("language"), str)
                    else None,
                    published_year=year,
                    cover_url=(links.get("thumbnail") or links.get("smallThumbnail")),
                    source=self.name,
                    source_url=info.get("infoLink"),
                    access_type=access_type,
                    access_url=preview,
                )
            )
        return books
