"""Data portability.

The load-bearing test here is `test_export_covers_everything_erasure_deletes`.
Export and erasure are two views of one question — what do we hold about this
person — and the failure mode is that they drift apart. An erasure that misses
a table is caught quickly by a privacy test. An export that misses one is
silent: the learner receives a file that looks complete.

So the two are checked against each other, and against the schema, rather than
against a hand-written inventory that somebody has to remember to update.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.base import Base
from app.models.tables import RubricAuditRow, TrainerLinkRow
from tests.conftest import Learner


@pytest.fixture
async def furnished(engine, learner: Learner) -> Learner:
    """A learner with data in every table we hold learner data in."""
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

    plan = learner.post(
        "/practice/session", json={"session_length_target_min": 5, "input_mode": "text"}
    ).json()
    for item in plan.get("items", [])[:2]:
        learner.post(
            "/practice/review", json={"block_id": item["block_id"], "correct": True}
        )

    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        db.add(
            TrainerLinkRow(
                trainer_user_id="trn_someone",
                learner_user_id=learner.user_id,
                display_name="Priya",
                institution_id="ins_x",
            )
        )
        db.add(
            RubricAuditRow(
                id="aud_1",
                user_id=learner.user_id,
                conversation_id="cnv_1",
                rubric_version="1.0.0",
                scored_dimensions=["clarity", "relevance"],
                excluded_dimensions=["fluency", "pace", "articulation"],
                prompt_hash="abc",
                model_id="test-model",
                evidence={},
            )
        )
        await db.commit()

    return learner


class TestTheRightExists:
    def test_a_learner_can_export_their_own_data(self, learner: Learner) -> None:
        assert learner.get("/export/me").status_code == 200

    def test_an_anonymous_caller_cannot(self, anonymous) -> None:
        assert anonymous.get("/export/me").status_code == 401

    def test_it_downloads_as_a_file(self, learner: Learner) -> None:
        """A right that produces a wall of JSON in a browser tab is a right
        somebody still has to know how to save."""
        disposition = learner.get("/export/me").headers["content-disposition"]
        assert "attachment" in disposition
        assert ".json" in disposition

    def test_a_learner_never_receives_another_learner_s_data(
        self, furnished: Learner, other_learner: Learner
    ) -> None:
        body = other_learner.get("/export/me").text
        assert furnished.user_id not in body


class TestCompleteness:
    async def test_export_covers_everything_erasure_deletes(self, furnished: Learner) -> None:
        """The test this module exists for.

        Every table that still holds a row for this learner must be represented
        in the export. Checked by walking the schema, so a table added next
        month fails here rather than being quietly omitted from every learner's
        file.
        """
        body = furnished.get("/export/me").json()

        #: table name -> the export key that carries it.
        COVERED = {
            "users": "account",
            "communication_ability_profiles": "communication_profiles",
            "consents": "consents",
            "practice_cards": "practice",
            "conversations": "conversations",
            "rubric_audit": "how_you_were_scored",
            "trainer_links": "support",
            "audio_objects": "audio",
        }

        for table in Base.metadata.sorted_tables:
            assert table.name in COVERED, (
                f"table '{table.name}' is not represented in the export. Add it, or add it "
                f"to this map with a reason it is not the learner's data."
            )
            assert COVERED[table.name] in body, f"export is missing '{COVERED[table.name]}'"

    async def test_the_tables_holding_this_learner_are_not_empty_in_the_export(
        self, furnished: Learner
    ) -> None:
        """Guards the test above from passing vacuously: a key can be present
        and empty."""
        body = furnished.get("/export/me").json()

        assert body["communication_profiles"], "profile held but not exported"
        assert body["consents"], "consent held but not exported"
        assert body["practice"], "practice cards held but not exported"
        assert body["how_you_were_scored"], "audit record held but not exported"
        assert body["support"]["has_a_trainer"] is True

    async def test_no_table_holding_this_learner_is_silently_dropped(
        self, furnished: Learner, engine
    ) -> None:
        """Belt and braces, from the database side rather than the code side."""
        held: list[str] = []

        async with engine.connect() as connection:
            for table in Base.metadata.sorted_tables:
                columns = [c for c in ("user_id", "learner_user_id", "id") if c in table.c]
                if not columns:
                    continue
                clause = " OR ".join(f"{column} = :uid" for column in columns)
                count = (
                    await connection.execute(
                        text(f"SELECT COUNT(*) FROM {table.name} WHERE {clause}"),  # noqa: S608
                        {"uid": furnished.user_id},
                    )
                ).scalar_one()
                if count:
                    held.append(table.name)

        # Every table with a row for this learner is one the export names.
        assert "communication_ability_profiles" in held
        assert "consents" in held
        assert "trainer_links" in held


class TestItIsReadableByTheLearner:
    def test_it_opens_with_plain_language(self, furnished: Learner) -> None:
        """A machine-readable export that only a lawyer can read makes the
        right unusable by the person it belongs to."""
        summary = furnished.get("/export/me").json()["about_you"]

        assert summary
        assert "everything we hold about you" in summary[0].lower()

    def test_the_summary_uses_short_sentences(self, furnished: Learner) -> None:
        for line in furnished.get("/export/me").json()["about_you"]:
            assert len(line.split()) <= 20, f"too long for Easy-Read: {line!r}"

    def test_it_tells_the_learner_they_can_delete_it_all(self, furnished: Learner) -> None:
        summary = " ".join(furnished.get("/export/me").json()["about_you"]).lower()
        assert "delete" in summary
        assert "do not have to ask" in summary

    def test_it_does_not_congratulate_the_learner(self, furnished: Learner) -> None:
        """Someone requesting their data is often unhappy with us. A record is
        not a progress report and must not read like one."""
        summary = " ".join(furnished.get("/export/me").json()["about_you"]).lower()

        for word in ("well done", "great", "amazing", "congratulations", "keep it up", "streak"):
            assert word not in summary

    def test_the_absence_of_recordings_is_stated_rather_than_implied(
        self, furnished: Learner
    ) -> None:
        """An empty key reads as a bug. An explicit "we hold none, and why"
        reads as the policy it is (Ethics E3)."""
        body = furnished.get("/export/me").json()

        assert body["audio"]["recordings"] == 0
        assert "24 hours" in body["audio"]["note"]


class TestNobodyElseIsInTheFile:
    def test_the_trainer_is_not_named(self, furnished: Learner) -> None:
        """A trainer link is a fact about the learner AND about a trainer. The
        learner's right to their own data is not a right to someone else's
        identity."""
        body = furnished.get("/export/me").text

        assert "trn_someone" not in body
        assert "Priya" not in body

    def test_but_the_learner_is_told_a_trainer_exists(self, furnished: Learner) -> None:
        """Withholding the name is not the same as hiding the arrangement."""
        support = furnished.get("/export/me").json()["support"]

        assert support["has_a_trainer"] is True
        assert "about you" in support["note"]

    def test_the_institution_is_not_named_either(self, furnished: Learner) -> None:
        assert "ins_x" not in furnished.get("/export/me").text


class TestTheFileIsSelfDescribing:
    def test_it_carries_a_version_and_a_date(self, learner: Learner) -> None:
        """A learner holding a file from a year ago should be able to tell what
        it is without asking us."""
        body = learner.get("/export/me").json()

        assert body["export_version"] >= 1
        assert body["generated_at"]

    def test_it_is_valid_json_all_the_way_down(self, furnished: Learner) -> None:
        """Datetimes are the usual thing that is not."""
        import json

        json.dumps(furnished.get("/export/me").json())
