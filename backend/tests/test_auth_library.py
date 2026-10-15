from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bookverse.database import get_session
from bookverse.main import app
from bookverse.models import Base, Book
from bookverse.schemas import Book as BookResult


class EmptyCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl):
        return None

    async def ping(self):
        return True


class DemoProvider:
    def __init__(self, name, external_id, source_url, access_type, access_url):
        self.name = name
        self.external_id = external_id
        self.source_url = source_url
        self.access_type = access_type
        self.access_url = access_url

    async def search(self, query, page, limit):
        return [
            BookResult(
                id=self.external_id,
                title="Shared Test Book",
                authors=["A. Writer"],
                source=self.name,
                source_url=self.source_url,
                access_type=self.access_type,
                access_url=self.access_url,
            )
        ]


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    book_id = uuid4()

    async def setup():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            session.add(Book(id=book_id, title="Seed Book"))
            await session.commit()

    import asyncio

    asyncio.run(setup())

    async def override_session():
        async with session_factory() as session:
            yield session

    try:
        app.dependency_overrides[get_session] = override_session
        app.state.seed_book_id = book_id
        with TestClient(app) as test_client:
            app.state.providers = [
                DemoProvider(
                    "open_library",
                    "/works/shared",
                    "https://openlibrary.org/works/shared",
                    "read",
                    "https://openlibrary.org/works/shared",
                ),
                DemoProvider(
                    "google_books",
                    "volume-shared",
                    "https://books.google.com/books?id=volume-shared",
                    "preview",
                    "https://books.google.com/books?id=volume-shared&printsec=frontcover",
                ),
            ]
            app.state.cache = EmptyCache()
            yield test_client
    finally:
        app.dependency_overrides.clear()
        import asyncio

        asyncio.run(engine.dispose())


def register(client: TestClient, email: str):
    return client.post(
        "/api/v1/auth/register", json={"email": email, "password": "safepassword123"}
    )


def test_register_login_refresh_and_logout_cookie_rotation(client: TestClient):
    created = register(client, "Reader@Example.com")
    assert created.status_code == 201
    first_cookie = created.cookies.get("bookverse_refresh")
    assert first_cookie
    assert created.headers.get("set-cookie", "").lower().find("httponly") >= 0

    duplicate = register(client, "reader@example.com")
    assert duplicate.status_code == 409

    access = created.json()["access_token"]
    assert (
        client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"}).json()[
            "email"
        ]
        == "reader@example.com"
    )

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != access
    second_cookie = refreshed.cookies.get("bookverse_refresh")
    assert second_cookie and second_cookie != first_cookie

    replay = client.post("/api/v1/auth/refresh", cookies={"bookverse_refresh": first_cookie})
    assert replay.status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh", cookies={"bookverse_refresh": second_cookie}
        ).status_code
        == 401
    )

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_library_is_private_to_each_authenticated_owner(client: TestClient):
    reader_a = register(client, "a@example.com").json()["access_token"]
    reader_b = register(client, "b@example.com").json()["access_token"]
    book_uuid = str(client.app.state.seed_book_id)
    put = client.put(
        f"/api/v1/library/{book_uuid}",
        headers={"Authorization": f"Bearer {reader_a}"},
        json={"status": "reading", "progress": 20},
    )
    assert put.status_code == 200
    assert (
        client.get("/api/v1/library", headers={"Authorization": f"Bearer {reader_a}"}).json()[
            "count"
        ]
        == 1
    )
    assert (
        client.get("/api/v1/library", headers={"Authorization": f"Bearer {reader_b}"}).json()[
            "count"
        ]
        == 0
    )


def test_private_library_requires_authentication(client: TestClient):
    assert client.get("/api/v1/library").status_code == 401


def test_search_merges_catalog_sources_and_details_stay_in_bookverse(client: TestClient):
    response = client.get("/api/v1/books", params={"q": "shared book"})
    assert response.status_code == 200
    book = response.json()["items"][0]
    assert {source["provider"] for source in book["sources"]} == {"open_library", "google_books"}
    assert book["id"] != "/works/shared"

    details = client.get(f"/api/v1/books/{book['id']}")
    assert details.status_code == 200
    assert len(details.json()["sources"]) == 2
    availability = client.get(f"/api/v1/books/{book['id']}/availability")
    assert {source["provider"] for source in availability.json()["sources"]} == {
        "open_library",
        "google_books",
    }
