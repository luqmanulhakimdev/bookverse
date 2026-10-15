import pytest

from bookverse.schemas import Book
from bookverse.search import AllProvidersFailed, search_books


class FakeProvider:
    def __init__(self, name, result=None, fail=False):
        self.name, self.result, self.fail = name, result or [], fail

    async def search(self, query, page, limit):
        if self.fail:
            raise RuntimeError("secret endpoint detail")
        return self.result


def book(title, provider):
    return Book(id=title, title=title, authors=["A. Writer"], source=provider)


@pytest.mark.asyncio
async def test_provider_failure_isolated_and_duplicates_removed():
    result = await search_books(
        "  dune  ",
        1,
        10,
        [
            FakeProvider("failed", fail=True),
            FakeProvider(
                "open_library", [book("Dune", "open_library"), book("Dune", "google_books")]
            ),
        ],
    )
    assert [b.title for b in result.items] == ["Dune"]
    assert result.providers[0].status == "error"
    assert result.total is None


@pytest.mark.asyncio
async def test_all_provider_failures_raise():
    with pytest.raises(AllProvidersFailed):
        await search_books("dune", 1, 10, [FakeProvider("one", fail=True)])


@pytest.mark.asyncio
async def test_empty_query_provider_set_is_failure():
    with pytest.raises(AllProvidersFailed):
        await search_books("dune", 1, 10, [])
