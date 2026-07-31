"""What must never appear in a log line, an error report, or an analytics event.

THE RULE
--------
Identifiers are logged. Content is not.

A `user_id` in a log line is how an incident gets diagnosed at 2am. A transcript
in a log line is a data breach with a retention policy attached — and for this
product specifically, it is a recording of a disabled person's speech sitting in
a third-party error tracker that nobody consented to.

This is applied by the logging formatter itself rather than at each call site,
because a rule that depends on every developer remembering it is a rule with a
half-life of about four months.
"""

from __future__ import annotations

import re
from typing import Any

#: Keys whose values are replaced wholesale. Matched case-insensitively against
#: the whole key and against snake/camel variants, because a field arriving as
#: `canonicalText` from the TypeScript side must be caught too.
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        # ── learner content ───────────────────────────────────────────────────
        "canonical_text",
        "transcript",
        "text",
        "utterance",
        "npc_utterance",
        "answer",
        "response_text",
        "easy_read",
        "message_body",
        "story_panels",
        "evidence_span",
        "override_reason",
        # ── biometric and media ───────────────────────────────────────────────
        "audio",
        "audio_base64",
        "audio_ref",
        "audio_key",
        "samples",
        "embedding",
        "speaker_embedding",
        "landmarks",
        "frames",
        # ── credentials ───────────────────────────────────────────────────────
        "password",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "authorization",
        "cookie",
        "secret",
        "service_token",
        "private_key",
        # ── direct identifiers ────────────────────────────────────────────────
        # user_id is deliberately NOT here: it is how an incident is diagnosed,
        # it is already a random identifier, and removing it would make the logs
        # useless without making anyone safer.
        "email",
        "phone",
        "full_name",
        "guardian_email",
        "date_of_birth",
    }
)

REDACTED = "[redacted]"

#: Depth cap. A cyclic or absurdly nested payload must not turn a log call into
#: a hang, and nothing legitimate in this system nests more than a few levels.
MAX_DEPTH = 6

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_BEARER = re.compile(r"(?i)bearer\s+[\w\-._~+/]+=*")


#: Split camelCase, but keep acronym runs together. The naive
#: `(?<!^)(?=[A-Z])` turns `TRANSCRIPT` into `t_r_a_n_s_c_r_i_p_t`, which matches
#: nothing — so an all-caps key sails straight through unredacted. That matters:
#: header maps and `os.environ` are routinely logged whole, and they carry
#: `AUTHORIZATION`, `API_KEY` and `PASSWORD` in exactly that shape.
_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _normalise(key: str) -> str:
    """`canonicalText`, `canonical_text`, `CANONICAL_TEXT` and
    `Canonical-Text` are all the same field."""
    key = str(key).strip().replace("-", " ").replace(" ", "_")
    key = _WORD_BOUNDARY.sub("_", key)
    return re.sub(r"_+", "_", key).lower().strip("_")


def is_sensitive(key: str) -> bool:
    return _normalise(str(key)) in SENSITIVE_KEYS


def scrub(value: Any, _depth: int = 0) -> Any:
    """Recursively replace sensitive values.

    Structure is preserved so a log line still shows *that* a transcript was
    present and how the payload was shaped — which is usually what you need to
    debug — without showing what anybody said.
    """
    if _depth > MAX_DEPTH:
        return "[truncated]"

    if isinstance(value, dict):
        return {
            key: REDACTED if is_sensitive(key) else scrub(item, _depth + 1)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        scrubbed = [scrub(item, _depth + 1) for item in value]
        return type(value)(scrubbed) if isinstance(value, (list, tuple)) else scrubbed

    if isinstance(value, str):
        return scrub_text(value)

    return value


def scrub_text(text: str) -> str:
    """Catch the two things that leak through free-text log messages.

    Email addresses and bearer tokens end up in exception messages and in
    third-party library output, where no key-based rule can see them.
    """
    return _BEARER.sub("Bearer " + REDACTED, _EMAIL.sub(REDACTED, text))
