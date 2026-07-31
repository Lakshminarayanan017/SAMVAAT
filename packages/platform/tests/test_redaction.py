"""Log redaction.

This module decides what reaches Sentry, the console, and any analytics sink. A
regression here does not raise — it quietly writes a disabled person's speech
transcript into a third-party error tracker that nobody consented to.

The rule it enforces: **identifiers are logged, content is not.**
"""

from __future__ import annotations

import pytest

from samvaad_platform.redaction import (
    MAX_DEPTH,
    REDACTED,
    SENSITIVE_KEYS,
    is_sensitive,
    scrub,
    scrub_text,
)


class TestSensitiveKeys:
    @pytest.mark.parametrize(
        "key",
        ["canonical_text", "transcript", "audio_ref", "speaker_embedding",
         "password", "authorization", "email", "evidence_span"],
    )
    def test_learner_content_and_credentials_are_sensitive(self, key: str) -> None:
        assert is_sensitive(key)

    def test_camel_case_from_the_typescript_side_is_caught(self) -> None:
        """The client speaks camelCase. A field arriving as `canonicalText` is
        the same field as `canonical_text` and must not slip through."""
        assert is_sensitive("canonicalText")
        assert is_sensitive("audioRef")
        assert is_sensitive("speakerEmbedding")

    def test_matching_is_case_insensitive(self) -> None:
        assert is_sensitive("TRANSCRIPT")
        assert is_sensitive("Authorization")

    def test_screaming_snake_case_is_caught(self) -> None:
        """Header maps and `os.environ` are routinely logged whole, and they
        carry credentials in exactly this shape. The first version of the
        normaliser turned TRANSCRIPT into t_r_a_n_s_c_r_i_p_t and matched
        nothing, so every all-caps key sailed through unredacted."""
        assert is_sensitive("API_KEY")
        assert is_sensitive("PASSWORD")
        assert is_sensitive("AUTHORIZATION")
        assert is_sensitive("SERVICE_TOKEN")

    def test_header_style_kebab_case_is_caught(self) -> None:
        assert is_sensitive("Authorization")
        assert is_sensitive("api-key")
        assert is_sensitive("Refresh-Token")

    def test_acronym_runs_do_not_break_the_split(self) -> None:
        """`audioRef` and `audioREF` are the same field."""
        assert is_sensitive("audioREF")
        assert is_sensitive("audioRef")

    def test_user_id_is_deliberately_not_redacted(self) -> None:
        """It is how an incident is diagnosed at 2am, it is already a random
        identifier, and removing it makes the logs useless without making anyone
        safer. This is a decision, not an oversight — hence a test."""
        assert not is_sensitive("user_id")
        assert not is_sensitive("session_id")
        assert not is_sensitive("block_id")

    def test_operational_fields_survive(self) -> None:
        for key in ["status", "latency_ms", "input_mode", "attempts", "model"]:
            assert not is_sensitive(key), f"{key} should remain loggable"


class TestScrub:
    def test_redacts_a_transcript_but_keeps_the_identifiers(self) -> None:
        result = scrub({
            "user_id": "usr_123",
            "session_id": "sess_9",
            "canonical_text": "could you please repeat that",
            "latency_ms": 240,
        })

        assert result["user_id"] == "usr_123"
        assert result["session_id"] == "sess_9"
        assert result["latency_ms"] == 240
        assert result["canonical_text"] == REDACTED

    def test_preserves_shape_so_a_log_line_is_still_debuggable(self) -> None:
        """You usually need to know *that* a transcript was present and how the
        payload was shaped, not what anybody said."""
        payload = {"a": {"transcript": "hello", "kept": 1}, "b": [1, 2]}
        result = scrub(payload)

        assert set(result) == {"a", "b"}
        assert set(result["a"]) == {"transcript", "kept"}
        assert result["a"]["kept"] == 1

    def test_recurses_into_nested_structures(self) -> None:
        result = scrub({"outer": {"inner": {"password": "hunter2", "ok": "fine"}}})

        assert result["outer"]["inner"]["password"] == REDACTED
        assert result["outer"]["inner"]["ok"] == "fine"

    def test_scrubs_inside_lists_of_dicts(self) -> None:
        result = scrub({"events": [{"transcript": "a"}, {"transcript": "b"}]})
        assert [e["transcript"] for e in result["events"]] == [REDACTED, REDACTED]

    def test_preserves_list_and_tuple_types(self) -> None:
        assert isinstance(scrub([1, 2]), list)
        assert isinstance(scrub((1, 2)), tuple)

    def test_depth_is_capped_so_a_log_call_cannot_hang(self) -> None:
        payload: dict = {"v": "leaf"}
        for _ in range(MAX_DEPTH + 4):
            payload = {"v": payload}

        # Must terminate and must not raise.
        assert "[truncated]" in repr(scrub(payload))

    def test_survives_a_self_referencing_payload(self) -> None:
        payload: dict = {"name": "loop"}
        payload["self"] = payload

        assert "[truncated]" in repr(scrub(payload))

    def test_leaves_non_string_scalars_alone(self) -> None:
        result = scrub({"count": 3, "ratio": 0.5, "ok": True, "nothing": None})
        assert result == {"count": 3, "ratio": 0.5, "ok": True, "nothing": None}

    def test_handles_an_empty_payload(self) -> None:
        assert scrub({}) == {}
        assert scrub([]) == []


class TestScrubText:
    """Free text is where key-based rules cannot help.

    Exception messages and third-party library output carry email addresses and
    bearer tokens with no key attached to them.
    """

    def test_removes_an_email_address(self) -> None:
        result = scrub_text("failed for learner ravi.kumar+test@example.co.in")
        assert "ravi.kumar" not in result
        assert "example.co.in" not in result
        assert REDACTED in result

    def test_removes_a_bearer_token(self) -> None:
        result = scrub_text("Authorization: Bearer eyJhbGciOi.J9-abc_123+xyz/def=")
        assert "eyJhbGciOi" not in result
        assert REDACTED in result

    def test_is_case_insensitive_about_bearer(self) -> None:
        assert "abc123def456" not in scrub_text("bearer abc123def456")

    def test_keeps_the_surrounding_message_readable(self) -> None:
        """A redactor that destroys the message defeats the point of logging."""
        result = scrub_text("upload failed for a@b.com after 3 retries")
        assert "upload failed" in result
        assert "after 3 retries" in result

    def test_leaves_ordinary_text_untouched(self) -> None:
        message = "speech service returned 503 after 2 attempts"
        assert scrub_text(message) == message

    def test_free_text_scrubbing_applies_through_scrub(self) -> None:
        result = scrub({"note": "contact guardian at parent@example.com"})
        assert "parent@example.com" not in result["note"]


class TestPolicyIntegrity:
    def test_every_sensitive_key_is_lowercase_snake_case(self) -> None:
        """The normaliser produces snake_case, so an entry in any other shape
        would silently never match."""
        for key in SENSITIVE_KEYS:
            assert key == key.lower(), f"{key} is not lowercase"
            assert " " not in key and "-" not in key, f"{key} is not snake_case"

    def test_the_biometric_and_credential_families_are_covered(self) -> None:
        """Voice is biometric and is the most sensitive thing this product
        handles. Losing one of these entries is a silent privacy regression."""
        for key in ["audio", "audio_ref", "samples", "embedding", "speaker_embedding"]:
            assert key in SENSITIVE_KEYS
        for key in ["password", "token", "api_key", "authorization", "private_key"]:
            assert key in SENSITIVE_KEYS
