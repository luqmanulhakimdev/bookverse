from ..schemas import Book
from .base import HttpProvider


class GutenbergProvider(HttpProvider):
    """Use Gutendex's catalog index and only link to ebook URLs it reports."""

    name = "gutenberg"

    async def search(self, query: str, page: int, limit: int) -> list[Book]:
        data = await self.get_json(self.base_url, {"search": query, "page": page})
        return self._map_books(data, limit)

    async def popular(self, page: int, limit: int) -> list[Book]:
        data = await self.get_json(self.base_url, {"sort": "popular", "page": page})
        return self._map_books(data, limit)

    def _map_books(self, data: dict, limit: int) -> list[Book]:
        results = data.get("results", [])
        if not isinstance(results, list):
            return []
        books = []
        for item in results[:limit]:
            if not isinstance(item, dict) or not item.get("id") or not item.get("title"):
                continue
            formats = item.get("formats") or {}
            if not isinstance(formats, dict):
                formats = {}
            epub = next(
                (
                    url
                    for mime, url in formats.items()
                    if isinstance(mime, str) and "epub" in mime and isinstance(url, str)
                ),
                None,
            )
            html = next(
                (
                    url
                    for mime, url in formats.items()
                    if isinstance(mime, str) and "text/html" in mime and isinstance(url, str)
                ),
                None,
            )
            copyright = item.get("copyright")
            if copyright is False:
                rights = "Project Gutenberg identifies this title as public domain in the United States; check local laws."
            elif copyright is True:
                rights = "Project Gutenberg marks this title copyrighted in the United States; access does not imply redistribution rights."
            else:
                rights = "Rights status is not established by this catalog response; check the source record and local laws."
            authors = item.get("authors") or []
            languages = item.get("languages") or []
            summaries = item.get("summaries") or []
            books.append(
                Book(
                    id=str(item["id"]),
                    title=str(item["title"]),
                    authors=[
                        str(author["name"])
                        for author in authors
                        if isinstance(author, dict) and isinstance(author.get("name"), str)
                    ],
                    description=next(
                        (summary for summary in summaries if isinstance(summary, str)), None
                    )
                    if isinstance(summaries, list)
                    else None,
                    language=languages[0] if languages and isinstance(languages[0], str) else None,
                    source=self.name,
                    source_url=f"https://www.gutenberg.org/ebooks/{item['id']}",
                    access_type="download" if epub else "read" if html else "metadata",
                    access_url=epub or html or f"https://www.gutenberg.org/ebooks/{item['id']}",
                    license_or_rights=rights,
                )
            )
        return books
