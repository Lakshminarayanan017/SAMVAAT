"""Grapheme to phoneme.

Turns the target text into the phoneme sequence that forced alignment expects.
This is the "what should they have said" half of the pipeline; ASR is the "what
did they actually say" half, and the two must not be confused.

Backed by CMUdict lookup with a neural fallback for out-of-vocabulary words
(`g2p_en`). Dictionary-first matters: a rule-based English letter-to-sound system
is wrong often enough that the resulting alignment targets would be wrong too,
and a wrong target produces a confident, entirely bogus pronunciation score.

Output is ARPAbet, the alphabet CMUdict and most English acoustic models use.

STRESS MARKERS ARE STRIPPED BY DEFAULT
--------------------------------------
CMUdict annotates vowels with 0/1/2 stress digits. We drop them for GOP,
deliberately: stress placement is prosody, and scoring a learner on lexical
stress would penalise regional accent and many speech differences under the
guise of pronunciation. Stress is analysed separately, as prosody (M7), where it
is reported as a coaching observation rather than as a score.
"""

from __future__ import annotations

import re
from functools import lru_cache

from pipeline.types import Phone

#: Non-phoneme tokens g2p_en emits: word gaps and punctuation.
_NOT_A_PHONE = re.compile(r"^[^A-Za-z]+$")

_STRESS = re.compile(r"\d$")


class G2pUnavailable(RuntimeError):
    """Raised when the G2P backend is not installed."""


@lru_cache(maxsize=1)
def _backend():
    try:
        from g2p_en import G2p
    except ImportError as error:  # pragma: no cover - environment dependent
        raise G2pUnavailable(
            "g2p_en is not installed. Run `pip install -r requirements.txt` in "
            "services/speech, then `python -m scripts.generate_phonemes` to warm "
            "the CMUdict cache."
        ) from error

    return G2p()


def is_available() -> bool:
    """Whether phonemisation can run. Reported by /capabilities."""
    try:
        _backend()
        return True
    except Exception:  # noqa: BLE001 - any failure means unavailable
        return False


def strip_stress(symbol: str) -> str:
    """`AH0` -> `AH`. See the module docstring for why."""
    return _STRESS.sub("", symbol)


def phonemise(text: str, keep_stress: bool = False) -> list[Phone]:
    """Phonemes for a phrase, each tagged with the word it belongs to.

    Word indices are what let a pronunciation score point at *which word* was
    difficult, rather than at a bare phoneme the learner cannot locate.
    """
    tokens = _backend()(text)

    phones: list[Phone] = []
    word_index = 0
    position = 0

    for token in tokens:
        if _NOT_A_PHONE.match(token):
            # A space or punctuation mark: the previous word has ended. Only
            # advance if that word actually produced phonemes, so trailing
            # punctuation does not create phantom words.
            if position > 0:
                word_index += 1
                position = 0
            continue

        symbol = token if keep_stress else strip_stress(token)
        phones.append(Phone(symbol=symbol, word_index=word_index, position_in_word=position))
        position += 1

    return phones


def phoneme_string(text: str, keep_stress: bool = False) -> str:
    """Space-separated phonemes, the form stored in the content bank."""
    return " ".join(phone.symbol for phone in phonemise(text, keep_stress))


def word_count(phones: list[Phone]) -> int:
    return max((phone.word_index for phone in phones), default=-1) + 1
