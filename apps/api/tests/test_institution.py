"""Institution analytics, end to end.

The suppression maths is unit-tested in test_anonymity.py. These check the
endpoint keeps the rules — which is where a careful module usually gets undone,
by a handler that helpfully returns the raw count "just for the total".
"""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.learning.anonymity import K
from app.models.tables import TrainerLinkRow, User
from app.security.auth import issue_token
from tests.conftest import Institution, Learner


class Enroller:
    """Creates learners already enrolled with an institution."""

    def __init__(self, app, engine, institution_id: str) -> None:
        self.app = app
        self.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        self.institution_id = institution_id
        self.client = None

    async def add(self, count: int, *, consenting: bool = True) -> list[Learner]:
        from fastapi.testclient import TestClient

        learners: list[Learner] = []

        with TestClient(self.app) as client:
            for index in range(count):
                user_id = f"gst_inst_{self.institution_id[-6:]}_{index}_{count}"

                async with self.sessionmaker() as db:
                    db.add(User(id=user_id, role="learner", is_guest=True))
                    db.add(
                        TrainerLinkRow(
                            trainer_user_id="trn_any",
                            learner_user_id=user_id,
                            institution_id=self.institution_id,
                        )
                    )
                    await db.commit()

                learner = Learner(client, user_id, issue_token(user_id))
                if consenting:
                    learner.post(
                        "/audio/consent",
                        json={"purpose": "institution_analytics", "granted": True},
                    )
                learners.append(learner)

        return learners


@pytest_asyncio.fixture
async def enrol(app, engine, institution: Institution) -> Enroller:
    return Enroller(app, engine, institution.user_id)


class TestRoleGate:
    def test_a_learner_cannot_reach_it(self, learner: Learner) -> None:
        assert learner.get("/institution/cohort").status_code == 403

    def test_a_trainer_cannot_reach_it_either(self, trainer) -> None:
        """A trainer sees named learners who consented to THEM. An institution
        sees anonymised aggregates. Neither role implies the other."""
        assert trainer.get("/institution/cohort").status_code == 403

    def test_an_anonymous_caller_is_refused(self, anonymous) -> None:
        assert anonymous.get("/institution/cohort").status_code == 401


class TestConsentGate:
    async def test_enrolment_is_not_agreement(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        await enrol.add(8, consenting=False)

        body = institution.get("/institution/cohort").json()

        assert body["enrolled"] == 8
        # Nobody agreed, so nothing is counted.
        assert body["learners"]["suppressed"] is True

    async def test_the_institution_is_told_how_many_opted_out(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        """They are entitled to know that, even though they cannot see who."""
        await enrol.add(6, consenting=True)
        await enrol.add(3, consenting=False)

        notes = " ".join(institution.get("/institution/cohort").json()["notes"])
        assert "have not agreed" in notes

    async def test_only_consenting_learners_are_counted(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        await enrol.add(7, consenting=True)
        await enrol.add(4, consenting=False)

        body = institution.get("/institution/cohort").json()

        assert body["enrolled"] == 11
        assert body["learners"]["count"] == 7


class TestSuppression:
    async def test_a_small_cohort_publishes_nothing(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        await enrol.add(K - 1, consenting=True)

        body = institution.get("/institution/cohort").json()

        assert body["learners"]["suppressed"] is True
        assert body["active_last_30_days"]["suppressed"] is True
        assert body["engagement_rate"] is None
        assert body["reliable_phrases"] == {}

    async def test_a_small_cohort_explains_why_it_is_empty(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        """An institution that does not understand a gap assumes a bug and asks
        us to remove the protection."""
        await enrol.add(2, consenting=True)

        notes = " ".join(institution.get("/institution/cohort").json()["notes"]).lower()
        assert "identifying someone" in notes

    async def test_a_suppressed_cell_carries_no_number(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        """Not zero-as-a-stand-in — a zero is itself a fact about a small group."""
        await enrol.add(3, consenting=True)

        body = institution.get("/institution/cohort").json()
        assert body["learners"]["count"] is None

    async def test_a_large_enough_cohort_publishes_the_headline(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        await enrol.add(K + 3, consenting=True)

        body = institution.get("/institution/cohort").json()
        assert body["learners"]["count"] == K + 3

    async def test_the_modality_mix_is_suppressed_like_everything_else(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        """The most identifying breakdown in the report. In a centre of twelve,
        "1 learner uses Indian Sign Language" names that person to everyone who
        works there."""
        learners = await enrol.add(10, consenting=True)

        # Nine typing, one signing.
        for learner in learners[:9]:
            learner.put(
                "/profile",
                json={
                    "input_channels": ["text"],
                    "output_channels": ["captioned_text"],
                    "text_complexity": "standard",
                    "speech_status": "typical",
                },
            )
        learners[9].put(
            "/profile",
            json={
                "input_channels": ["sign"],
                "output_channels": ["isl", "captioned_text"],
                "text_complexity": "standard",
                "speech_status": "nonverbal",
            },
        )

        mix = institution.get("/institution/cohort").json()["modality_mix"]

        # The single ISL learner must not be published, and neither may the
        # majority cell — 10 minus 9 identifies them by subtraction.
        assert mix.get("isl", {}).get("count") is None
        assert mix.get("captioned_text", {}).get("count") is None


class TestNothingIdentifying:
    async def test_no_learner_id_appears_anywhere_in_the_report(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        learners = await enrol.add(K + 5, consenting=True)

        body = institution.get("/institution/cohort").text

        for learner in learners:
            assert learner.user_id not in body

    async def test_there_is_no_way_to_narrow_the_cohort(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        """Arbitrary filtering is how aggregate data gets turned back into
        individuals: ask for the intersection of enough attributes and you have
        named someone. The endpoint takes no filter parameters at all."""
        await enrol.add(K + 3, consenting=True)

        # Any filter-shaped query is simply ignored, not honoured.
        plain = institution.get("/institution/cohort").json()
        filtered = institution.get(
            "/institution/cohort",
            params={"output_channel": "isl", "min_age": 18, "learner_id": "gst_x"},
        ).json()

        assert plain["learners"] == filtered["learners"]
        assert plain["modality_mix"] == filtered["modality_mix"]

    async def test_the_report_never_returns_a_per_learner_row(
        self, institution: Institution, enrol: Enroller
    ) -> None:
        await enrol.add(K + 5, consenting=True)

        body = institution.get("/institution/cohort").json()

        for key in body:
            assert "learner_user_id" not in key
            assert "learners" not in key or key == "learners"
        assert not isinstance(body["learners"], list)
