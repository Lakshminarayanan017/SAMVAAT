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

import logging
import re
from functools import lru_cache

from pipeline.types import Phone

log = logging.getLogger("samvaad.speech.g2p")

#: Non-phoneme tokens g2p_en emits: word gaps and punctuation.
_NOT_A_PHONE = re.compile(r"^[^A-Za-z]+$")

_STRESS = re.compile(r"\d$")

#: NLTK corpora g2p_en reaches for at call time, not at construction time.
#: The part-of-speech tagger disambiguates homographs — "read" as past tense is
#: R EH D, as present tense R IY D — so without it the phonemes are wrong for a
#: whole class of words rather than merely absent.
_NLTK_REQUIREMENTS: tuple[tuple[str, str], ...] = (
    ("taggers/averaged_perceptron_tagger_eng", "averaged_perceptron_tagger_eng"),
    ("corpora/cmudict", "cmudict"),
)


class G2pUnavailable(RuntimeError):
    """Raised when the G2P backend is not installed or cannot run."""


@lru_cache(maxsize=1)
def ensure_nltk_data() -> bool:
    """Make sure the corpora g2p_en needs are present, downloading if not.

    g2p_en constructs happily without them and then raises `LookupError` on the
    first call. A backend that reports itself available and fails on use is worse
    than one that is honestly unavailable, so we resolve the data eagerly and let
    `is_available` reflect the real answer.

    Returns False rather than raising when the download is impossible — an
    offline build host is a legitimate state, and the caller degrades to the
    non-speech paths that the rest of the product is built to provide.
    """
    try:
        import nltk
    except ImportError:  # pragma: no cover - g2p_en depends on nltk
        return False

    for path, package in _NLTK_REQUIREMENTS:
        try:
            nltk.data.find(path)
        except LookupError:
            log.info("downloading NLTK corpus %s for phonemisation", package)
            try:
                nltk.download(package, quiet=True)
                nltk.data.find(path)
            except Exception:  # noqa: BLE001 - offline, sandboxed, or read-only
                log.warning(
                    "NLTK corpus %s unavailable; phonemisation and therefore GOP are off. "
                    "Run `python -m scripts.warm_g2p` on a host with network access.",
                    package,
                )
                return False

    return True


@lru_cache(maxsize=1)
def _backend():
    try:
        from g2p_en import G2p
    except ImportError as error:  # pragma: no cover - environment dependent
        raise G2pUnavailable(
            "g2p_en is not installed. Run `pip install -r requirements.txt` in "
            "services/speech, then `python -m scripts.warm_g2p` to warm the caches."
        ) from error

    if not ensure_nltk_data():
        raise G2pUnavailable(
            "g2p_en is installed but its NLTK corpora are missing and could not be "
            "downloaded. Run `python -m scripts.warm_g2p` on a host with network access."
        )

    return G2p()


@lru_cache(maxsize=1)
def is_available() -> bool:
    """Whether phonemisation can run. Reported by /capabilities.

    Probes with a real phonemisation rather than merely constructing the backend.
    g2p_en's constructor succeeds without its corpora and only fails when called,
    so a construction-only check reports a capability the service does not have —
    and the client, trusting it, leaves a learner waiting for feedback that is
    never coming.
    """
    try:
        return bool(_backend()("test"))
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


# ── ARPAbet to IPA ───────────────────────────────────────────────────────────
#
# CMUdict speaks ARPAbet. The phoneme acoustic model that produces the posteriors
# GOP is computed over speaks IPA. Something has to translate, and doing it in
# one audited table beats scattering `if symbol == "AA"` through the pipeline.
#
# A silent mismatch here is the worst class of bug this service can have: every
# utterance would be aligned against the wrong targets, GOP would be computed
# confidently over nonsense, and the resulting numbers would look entirely
# plausible. The mapping is asserted complete against the ARPAbet inventory by
# `tests/test_pipeline.py`.


#: The 39 ARPAbet phonemes of American English, to their IPA equivalents as used
#: by the espeak-based phoneme models. Vowel choices follow the General American
#: conventions CMUdict itself documents.
_ARPABET_TO_IPA: dict[str, str] = {
    # vowels
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ",
    "AY": "aɪ", "EH": "ɛ", "ER": "ɚ", "EY": "eɪ", "IH": "ɪ",
    "IY": "i", "OW": "oʊ", "OY": "ɔɪ", "UH": "ʊ", "UW": "u",
    # consonants
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f",
    "G": "ɡ", "HH": "h", "JH": "dʒ", "K": "k", "L": "l",
    "M": "m", "N": "n", "NG": "ŋ", "P": "p", "R": "ɹ",
    "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v",
    "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ",
}


def arpabet_to_ipa() -> dict[str, str]:
    """The ARPAbet-to-IPA mapping, as a copy.

    Returned by value so a caller mutating the result — a plausible thing to do
    while adding a language — cannot silently corrupt alignment for every
    subsequent request in the process.
    """
    return dict(_ARPABET_TO_IPA)


#: Every ARPAbet symbol the phonemiser can emit. Exposed so a test can assert
#: the IPA table covers all of them rather than discovering a gap in production.
ARPABET_INVENTORY: frozenset[str] = frozenset(_ARPABET_TO_IPA)
