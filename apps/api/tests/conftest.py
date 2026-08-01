"""Shared test fixtures.

Every test runs against a real database — in-memory SQLite, created and dropped
per test. That is a deliberate choice over mocking the repositories: constraints,
transactions, cascades and JSON round-tripping are exactly the things that break
in production, and a mock proves none of them.

It costs about a millisecond per test.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Set before app.config is imported anywhere, so the cached settings pick it up.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from uuid import uuid4  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.tables import User  # noqa: E402
from app.security.auth import issue_token, new_user_id  # noqa: E402


@pytest_asyncio.fixture
async def engine() -> AsyncIterator:
    # StaticPool keeps one connection for the whole engine. Without it every
    # session would get a different, empty in-memory database.
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield test_engine
    await test_engine.dispose()


@pytest.fixture
def app(engine):
    """The application, wired to the test database."""
    application = create_app()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    application.dependency_overrides[get_session] = override
    return application


@pytest.fixture
def anonymous(app) -> Iterator[TestClient]:
    """A client with no token. Used to prove endpoints actually require one."""
    with TestClient(app) as client:
        yield client


class Learner:
    """An authenticated learner, and a client that speaks as them."""

    def __init__(self, client: TestClient, user_id: str, token: str) -> None:
        self.client = client
        self.user_id = user_id
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, url: str, **kwargs):
        return self.client.get(url, headers=self.headers, **kwargs)

    def post(self, url: str, **kwargs):
        return self.client.post(url, headers=self.headers, **kwargs)

    def put(self, url: str, **kwargs):
        return self.client.put(url, headers=self.headers, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.client.delete(url, headers=self.headers, **kwargs)


class Trainer(Learner):
    """Same interface, a trainer token."""


class Institution(Learner):
    """Same interface, an institution token."""


def _sign_up(client: TestClient) -> Learner:
    response = client.post("/auth/guest")
    assert response.status_code == 200, response.text
    body = response.json()
    return Learner(client, body["user_id"], body["access_token"])


@pytest.fixture
def learner(app) -> Iterator[Learner]:
    with TestClient(app) as client:
        yield _sign_up(client)


@pytest.fixture
def other_learner(app) -> Iterator[Learner]:
    """A second learner, for proving isolation.

    A separate client on the same app and the same database — which is what
    makes "can A read B's interview?" a real question rather than a staged one.
    """
    with TestClient(app) as client:
        yield _sign_up(client)


@pytest_asyncio.fixture
async def trainer(app, engine) -> Trainer:
    """A trainer: a real user row with the role, and a token that matches.

    There is no self-service trainer signup, deliberately — a trainer account is
    provisioned by an institution. Tests create the row directly rather than
    inventing an endpoint that should not exist.
    """
    user_id = f"trn_{uuid4().hex[:12]}"

    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        db.add(User(id=user_id, role="trainer", is_guest=False))
        await db.commit()

    with TestClient(app) as client:
        yield Trainer(client, user_id, issue_token(user_id, role="trainer", is_guest=False))


@pytest_asyncio.fixture
async def institution(app, engine) -> Institution:
    """An institution account.

    Its id doubles as the `institution_id` on trainer links, so a test can
    enrol learners into it without inventing a second identifier.
    """
    user_id = f"ins_{uuid4().hex[:12]}"

    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        db.add(User(id=user_id, role="institution", is_guest=False))
        await db.commit()

    with TestClient(app) as client:
        yield Institution(
            client, user_id, issue_token(user_id, role="institution", is_guest=False)
        )


@pytest.fixture
def forged_token() -> str:
    """A validly signed token for a user that was never created.

    Proves the difference between "the signature is good" and "this learner
    exists" — a token alone must not conjure data.
    """
    return issue_token(new_user_id(guest=True))
