"""Personalised ASR adaptation (M8).

The serving half. Training runs on a GPU elsewhere; what is tested here is the
half that decides whether its output is allowed anywhere near a learner.

The property that matters: an adapter that does not measurably help is never
served. Personalisation that makes recognition worse is not a degraded feature,
it is an actively harmful one — and "we tuned this to your voice" makes the
learner feel it is their fault.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from pipeline.adapters import (
    ENROLMENT_PHRASE_COUNT,
    MIN_RELATIVE_WER_REDUCTION,
    AdapterEvaluation,
    AdapterRecord,
    EnrolmentProgress,
    FileAdapterRegistry,
    evaluate_adapter,
    promote,
    select_enrolment_phrases,
    word_error_rate,
)


def evaluation(before: float, after: float, n: int = 6) -> AdapterEvaluation:
    return AdapterEvaluation(
        wer_before=before,
        wer_after=after,
        held_out_utterances=n,
        evaluated_at=datetime.now(timezone.utc),
    )


class TestWordErrorRate:
    def test_a_perfect_transcription_scores_zero(self) -> None:
        phrase = "could you please repeat that"
        assert word_error_rate(phrase, phrase) == 0.0

    def test_one_wrong_word_in_five(self) -> None:
        assert word_error_rate("i have finished the batch", "i have completed the batch") == 0.2

    def test_an_empty_reference_does_not_divide_by_zero(self) -> None:
        assert word_error_rate("", "anything at all") == 0.0

    def test_punctuation_and_case_do_not_count_as_errors(self) -> None:
        assert word_error_rate("Good morning!", "good morning") == 0.0


class TestGuardrail:
    def test_a_clear_improvement_is_deployed(self) -> None:
        assert evaluation(0.60, 0.30).passes_guardrail is True

    def test_a_regression_is_never_deployed(self) -> None:
        """The case this whole mechanism exists for."""
        assert evaluation(0.40, 0.55).passes_guardrail is False

    def test_a_marginal_gain_inside_the_noise_is_not_deployed(self) -> None:
        """A 5% relative gain on six utterances is noise. Deploying on noise
        means some learners get worse recognition and are told it is better."""
        assert evaluation(0.40, 0.38).passes_guardrail is False

    def test_the_bar_is_the_documented_one(self) -> None:
        """Sourced from the execution plan §9.4. A silent change here would
        lower the standard for every learner at once."""
        assert MIN_RELATIVE_WER_REDUCTION == 0.25

        just_under = evaluation(0.40, 0.40 * (1 - MIN_RELATIVE_WER_REDUCTION + 0.01))
        just_over = evaluation(0.40, 0.40 * (1 - MIN_RELATIVE_WER_REDUCTION - 0.01))

        assert just_under.passes_guardrail is False
        assert just_over.passes_guardrail is True

    def test_too_few_held_out_utterances_is_not_enough_evidence(self) -> None:
        assert evaluation(0.60, 0.20, n=3).passes_guardrail is False
        assert evaluation(0.60, 0.20, n=5).passes_guardrail is True

    def test_promote_is_the_only_route_to_deployment(self) -> None:
        """An optimistically constructed record must not be servable."""
        record = AdapterRecord(
            user_id="p3-arjun",
            path=None,
            base_model="openai/whisper-small",
            trained_at=datetime.now(timezone.utc),
        )
        assert record.deployed is False

        assert promote(record, evaluation(0.60, 0.30)).deployed is True
        assert promote(record, evaluation(0.60, 0.58)).deployed is False


class TestLearnerMessage:
    def test_a_successful_adapter_is_phrased_as_the_app_improving(self) -> None:
        """Not 'you are 34% clearer'. That would be false, and it is the exact
        framing this product exists to refuse."""
        message = evaluation(0.60, 0.30).learner_message()

        assert "the app" in message.lower()
        assert "50%" in message
        for word in ("you are", "your speech is", "clearer", "better speaker"):
            assert word not in message.lower()

    def test_a_failed_adapter_says_nothing_has_changed(self) -> None:
        message = evaluation(0.40, 0.42).learner_message()

        assert "still learning" in message.lower()
        # Never reports a negative improvement as though it were a result.
        assert "%" not in message


class TestEvaluateAdapter:
    def test_pairs_must_cover_the_same_utterances(self) -> None:
        """Comparing an adapter against a different set of clips than the base
        is the easiest way to manufacture an improvement that is not real."""
        with pytest.raises(ValueError, match="same held-out utterances"):
            evaluate_adapter([("a", "a")], [("a", "a"), ("b", "b")])

    def test_computes_mean_word_error_rate_on_both_sides(self) -> None:
        result = evaluate_adapter(
            pairs_before=[("good morning", "good mourning sir"), ("thank you", "tank")],
            pairs_after=[("good morning", "good morning"), ("thank you", "thank you")],
        )

        assert result.wer_after == 0.0
        assert result.wer_before > 0.0
        assert result.held_out_utterances == 2


class TestEnrolmentProgress:
    def test_is_resumable_and_never_a_wall(self) -> None:
        progress = EnrolmentProgress(user_id="p3-arjun", completed=12)

        assert progress.is_complete is False
        assert progress.fraction == pytest.approx(12 / ENROLMENT_PHRASE_COUNT)
        assert "18 to go" in progress.message()
        # No deadline, no urgency, and an explicit promise that effort is kept.
        assert "saves as you go" in progress.message()

    def test_completion_is_stated_plainly(self) -> None:
        progress = EnrolmentProgress(user_id="p3-arjun", completed=ENROLMENT_PHRASE_COUNT)

        assert progress.is_complete is True
        assert "finished" in progress.message().lower()

    def test_the_message_never_pressures(self) -> None:
        for completed in (0, 5, 29, 30):
            message = EnrolmentProgress("u", completed=completed).message().lower()
            for word in ("must", "required", "hurry", "quickly", "deadline", "only"):
                assert word not in message


class TestEnrolmentPhraseSelection:
    def _block(self, block_id: str, phonemes: str, text: str = "a phrase") -> dict:
        return {
            "id": block_id,
            "canonical_text": text,
            "difficulty": 2,
            "representations": {"phonemes": phonemes},
        }

    def test_prefers_phonetic_coverage_over_repetition(self) -> None:
        """Thirty random workplace phrases over-represent the same handful of
        common words. Thirty chosen for coverage exercise the sounds the adapter
        actually has to learn."""
        blocks = [
            self._block("a", "G UH D M AO R N IH NG"),
            self._block("b", "G UH D M AO R N IH NG"),  # identical coverage
            self._block("c", "TH AE NG K Y UW V EH R IY M AH CH"),
        ]

        chosen = select_enrolment_phrases(blocks, count=2)
        assert {block["id"] for block in chosen} == {"a", "c"}

    def test_returns_the_requested_count_even_without_new_coverage(self) -> None:
        blocks = [self._block(str(n), "G UH D") for n in range(10)]
        assert len(select_enrolment_phrases(blocks, count=4)) == 4

    def test_never_returns_more_than_asked(self) -> None:
        blocks = [self._block(str(n), f"P{n} AH") for n in range(50)]
        assert len(select_enrolment_phrases(blocks, count=30)) == 30

    def test_handles_an_empty_bank(self) -> None:
        assert select_enrolment_phrases([], count=30) == []

    def test_blocks_without_phonemes_are_usable_but_not_preferred(self) -> None:
        blocks = [
            {"id": "no-phonemes", "canonical_text": "hello", "representations": {}},
            self._block("rich", "G UH D M AO R N IH NG"),
        ]
        assert select_enrolment_phrases(blocks, count=1)[0]["id"] == "rich"


class TestFileAdapterRegistry:
    def test_round_trips_a_record(self, tmp_path) -> None:
        registry = FileAdapterRegistry(tmp_path)
        record = promote(
            AdapterRecord(
                user_id="p3-arjun",
                path=tmp_path / "p3-arjun",
                base_model="openai/whisper-small",
                trained_at=datetime.now(timezone.utc),
            ),
            evaluation(0.62, 0.31),
        )

        registry.save(record)
        loaded = registry.get("p3-arjun")

        assert loaded is not None
        assert loaded.deployed is True
        assert loaded.base_model == "openai/whisper-small"
        assert loaded.evaluation.wer_after == pytest.approx(0.31)

    def test_an_unknown_learner_returns_none_rather_than_raising(self, tmp_path) -> None:
        assert FileAdapterRegistry(tmp_path).get("nobody") is None

    def test_a_corrupt_sidecar_disables_the_adapter_rather_than_crashing(self, tmp_path) -> None:
        """The correct behaviour after a partial restore: fall back to base ASR
        silently. A learner recording something must never see an error because
        a metadata file was truncated."""
        directory = tmp_path / "p3-arjun"
        directory.mkdir()
        (directory / "adapter.json").write_text("{ not json", encoding="utf-8")

        assert FileAdapterRegistry(tmp_path).get("p3-arjun") is None

    def test_only_deployed_adapters_are_listed(self, tmp_path) -> None:
        registry = FileAdapterRegistry(tmp_path)

        for user_id, after in [("helped", 0.20), ("did-not-help", 0.59)]:
            registry.save(
                promote(
                    AdapterRecord(
                        user_id=user_id,
                        path=tmp_path / user_id,
                        base_model="openai/whisper-small",
                        trained_at=datetime.now(timezone.utc),
                    ),
                    evaluation(0.60, after),
                )
            )

        assert [record.user_id for record in registry.list_deployed()] == ["helped"]

    def test_the_sidecar_carries_the_evaluation(self, tmp_path) -> None:
        """A host with the weights but not the eval record must refuse to serve
        them — weights on disk are not permission to use them."""
        registry = FileAdapterRegistry(tmp_path)
        registry.save(
            promote(
                AdapterRecord(
                    user_id="p3-arjun",
                    path=tmp_path / "p3-arjun",
                    base_model="openai/whisper-small",
                    trained_at=datetime.now(timezone.utc),
                ),
                evaluation(0.60, 0.25),
            )
        )

        payload = json.loads((tmp_path / "p3-arjun" / "adapter.json").read_text(encoding="utf-8"))
        assert payload["evaluation"]["wer_before"] == pytest.approx(0.60)
        assert payload["deployed"] is True


class TestRetrainTrigger:
    def test_fires_after_enough_new_confirmed_transcriptions(self) -> None:
        record = AdapterRecord(
            user_id="p3-arjun",
            path=None,
            base_model="openai/whisper-small",
            trained_at=datetime.now(timezone.utc),
            new_samples_since_training=25,
        )
        assert record.should_retrain() is True

    def test_does_not_fire_on_a_handful(self) -> None:
        record = AdapterRecord(
            user_id="p3-arjun",
            path=None,
            base_model="openai/whisper-small",
            trained_at=datetime.now(timezone.utc),
            new_samples_since_training=4,
        )
        assert record.should_retrain() is False
