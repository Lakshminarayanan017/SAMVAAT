"""Erasure, checked table by table.

`DELETE /auth/me` deletes a list of things. This checks the list is the whole
list — by walking the actual SQLAlchemy metadata rather than by naming tables,
so a table added next month fails this test instead of quietly surviving
erasure.

That distinction matters more here than almost anywhere else in the codebase.
The rows involved are a communication profile that records whether someone is
non-verbal, a consent ledger, and a trainer link that carries the learner's
real name. "We deleted most of it" is not erasure.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.base import Base
from app.models.tables import CapRow, ConsentRow, TrainerLinkRow, User
from tests.conftest import Learner

#: Columns that hold the id of the learner a row is about. A table whose
#: learner-identifying column is not in here is a table this test cannot check,
#: which is itself a failure — see `test_every_table_is_accounted_for`.
LEARNER_COLUMNS = ("user_id", "learner_user_id")

#: Tables that legitimately survive one learner's erasure.
NOT_ABOUT_ONE_LEARNER = {
    "users",  # the row itself is deleted; checked separately
}


async def _rows_mentioning(engine, user_id: str) -> dict[str, int]:
    """Every row, in every table, that still names this learner."""
    remaining: dict[str, int] = {}

    async with engine.connect() as connection:
        for table in Base.metadata.sorted_tables:
            columns = [c for c in LEARNER_COLUMNS if c in table.c]
            if not columns:
                continue

            clause = " OR ".join(f"{column} = :uid" for column in columns)
            count = (
                await connection.execute(
                    text(f"SELECT COUNT(*) FROM {table.name} WHERE {clause}"),  # noqa: S608
                    {"uid": user_id},
                )
            ).scalar_one()

            if count:
                remaining[table.name] = count

    return remaining


@pytest.fixture
async def furnished(app, engine, learner: Learner):
    """A learner with something in every table erasure is meant to clear."""
    learner.put(
        "/profile",
        json={
            "input_channels": ["aac"],
            "output_channels": ["pictograph", "easy_read"],
            "text_complexity": "easy_read",
            "speech_status": "nonverbal",
        },
    )
    learner.post("/audio/consent", json={"purpose": "trainer_visibility", "granted": True})

    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        db.add(
            TrainerLinkRow(
                trainer_user_id="trn_someone",
                learner_user_id=learner.user_id,
                display_name="Priya",
                institution_id="ins_x",
            )
        )
        await db.commit()

    return learner


class TestNothingIsLeftBehind:
    async def test_no_row_anywhere_still_names_the_learner(self, furnished, engine) -> None:
        """The whole test, in one assertion.

        Deliberately not a list of tables to check: a list is a thing somebody
        forgets to extend. This walks the schema.
        """
        user_id = furnished.user_id

        before = await _rows_mentioning(engine, user_id)
        assert before, "fixture wrote nothing — the test would pass vacuously"

        assert furnished.delete("/auth/me").status_code == 200

        after = await _rows_mentioning(engine, user_id)
        assert after == {}, f"erasure left data behind in {after}"

    async def test_the_user_row_itself_is_gone(self, furnished, engine) -> None:
        furnished.delete("/auth/me")

        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            assert await db.get(User, furnished.user_id) is None

    async def test_the_communication_profile_is_gone(self, furnished, engine) -> None:
        """It records that this learner is non-verbal. That is health-adjacent
        data about a disabled person, and it is the row most likely to be left
        behind because a cascade was assumed rather than checked."""
        furnished.delete("/auth/me")

        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            rows = (await db.execute(_select(CapRow, furnished.user_id))).scalars().all()
            assert rows == []

    async def test_the_consent_ledger_is_gone(self, furnished, engine) -> None:
        furnished.delete("/auth/me")

        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            rows = (await db.execute(_select(ConsentRow, furnished.user_id))).scalars().all()
            assert rows == []

    async def test_the_trainer_link_is_gone(self, furnished, engine) -> None:
        """It carries `display_name` — the learner's actual name, stored
        outside their own account because trainers onboard learners who have
        not typed yet. Erasure that leaves this behind leaves a name behind."""
        furnished.delete("/auth/me")

        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            rows = (
                (
                    await db.execute(
                        _select(TrainerLinkRow, furnished.user_id, column="learner_user_id")
                    )
                )
                .scalars()
                .all()
            )
            assert rows == []


class TestTheTestItself:
    def test_every_table_is_accounted_for(self) -> None:
        """A table that names a learner under some other column name would be
        invisible to `_rows_mentioning`, and this suite would pass while
        checking nothing about it."""
        unchecked = [
            table.name
            for table in Base.metadata.sorted_tables
            if table.name not in NOT_ABOUT_ONE_LEARNER
            and not any(column in table.c for column in LEARNER_COLUMNS)
        ]

        assert unchecked == [], (
            f"{unchecked} name a learner by some column this test does not know about. "
            f"Add it to LEARNER_COLUMNS, or to NOT_ABOUT_ONE_LEARNER with a reason."
        )

    async def test_erasure_does_not_touch_another_learner(
        self, furnished, other_learner: Learner, engine
    ) -> None:
        """The obvious way to make the assertion above pass is to delete too
        much."""
        other_learner.put(
            "/profile",
            json={
                "input_channels": ["text"],
                "output_channels": ["captioned_text"],
                "text_complexity": "standard",
                "speech_status": "typical",
            },
        )

        furnished.delete("/auth/me")

        assert await _rows_mentioning(engine, other_learner.user_id) != {}


def _select(model, user_id: str, column: str = "user_id"):
    from sqlalchemy import select

    return select(model).where(getattr(model, column) == user_id)
