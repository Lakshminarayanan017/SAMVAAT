"""Retrieval over the Workplace Language Bank.

The grounding that stops the model inventing content. Every generated turn is
built from a context containing phrases the learner has actually been taught, and
`target_phrases` on the response must come from this bank — that constraint is
what makes the role-play a practice exercise rather than a chatbot.

WHY THIS IS NOT A VECTOR DATABASE
---------------------------------
226 phrases. A brute-force scan over 226 embeddings takes microseconds, fits in
a few hundred kilobytes, and has no operational surface at all. Standing up
pgvector for a corpus this size would be infrastructure serving a diagram rather
than a workload.

The interface is written so that swapping in pgvector is a class, not a
refactor: `PhraseIndex.search` is the only method anything calls. When the corpus
outgrows memory — which for a curated bank means a different product, not a
bigger version of this one — the swap is local.

EMBEDDINGS ARE OPTIONAL
-----------------------
With `sentence-transformers` installed, retrieval is semantic. Without it, the
index falls back to a scored keyword match over intent, tags and text. The
fallback is genuinely good on this corpus because the corpus is tagged by hand —
and it means the service runs, and CI runs, with no model download.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache

log = logging.getLogger("samvaad.genai.retrieval")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

#: Retrieved phrases per turn. Enough to ground the generation, few enough that
#: the context stays short — and context length is the main lever on cost.
DEFAULT_TOP_K = 8


@dataclass(frozen=True)
class Retrieved:
    block_id: str
    canonical_text: str
    intent: str
    difficulty: int
    scenario_tags: tuple[str, ...]
    score: float

    def as_context_line(self) -> str:
        """One line of prompt context. Compact on purpose — this is multiplied
        by top-k and by every turn of every conversation."""
        return f'- {self.block_id} ({self.intent}, level {self.difficulty}): "{self.canonical_text}"'


@dataclass
class Query:
    """What to retrieve for.

    Structured rather than a single string because the useful filters here are
    categorical — tags and difficulty — and collapsing them into free text
    throws away the hand-tagging that makes the corpus valuable.
    """

    text: str = ""
    scenario_tags: tuple[str, ...] = ()
    #: Inclusive difficulty window. The learner's current tier plus one, so
    #: retrieval supports the Zone of Proximal Development rather than fighting it.
    min_difficulty: int = 1
    max_difficulty: int = 5
    #: Phrases the learner has recently got wrong. Boosted, because the most
    #: useful thing a role-play can do is give them another chance at those.
    error_signature: tuple[str, ...] = ()
    exclude_ids: frozenset[str] = frozenset()


class PhraseIndex:
    """In-memory index over the built phrase bank."""

    def __init__(self, blocks: list[dict]) -> None:
        self.blocks = blocks
        self._by_id = {block["id"]: block for block in blocks}
        self._embeddings = None
        self._tokens: dict[str, set[str]] = {
            block["id"]: _tokenise(
                f"{block['canonical_text']} {block.get('intent', '')} "
                f"{' '.join(block.get('scenario_tags', []))}"
            )
            for block in blocks
        }
        self._document_frequency = _document_frequency(self._tokens)

    # ── public interface ─────────────────────────────────────────────────────

    def search(self, query: Query, top_k: int = DEFAULT_TOP_K) -> list[Retrieved]:
        """The only retrieval method anything calls."""
        candidates = [
            block
            for block in self.blocks
            if self._passes_filters(block, query)
        ]

        if not candidates:
            # Filters too narrow. Widening beats returning nothing: an empty
            # context produces an ungrounded generation, which is precisely the
            # failure mode retrieval exists to prevent.
            log.info("no phrases matched the filters; widening to the difficulty window only")
            candidates = [
                block
                for block in self.blocks
                if query.min_difficulty <= block["difficulty"] <= query.max_difficulty
                and block["id"] not in query.exclude_ids
            ] or self.blocks

        scored = [
            (self._score(block, query), block)
            for block in candidates
        ]
        scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))

        return [
            Retrieved(
                block_id=block["id"],
                canonical_text=block["canonical_text"],
                intent=block.get("intent", ""),
                difficulty=block["difficulty"],
                scenario_tags=tuple(block.get("scenario_tags", [])),
                score=round(score, 4),
            )
            for score, block in scored[:top_k]
        ]

    def get(self, block_id: str) -> dict | None:
        return self._by_id.get(block_id)

    def contains(self, block_id: str) -> bool:
        return block_id in self._by_id

    def known_ids(self) -> frozenset[str]:
        """Every phrase id. The grounding check validates `target_phrases`
        against this, which is what stops the model citing a phrase we do not
        teach and the client rendering a broken reference."""
        return frozenset(self._by_id)

    # ── scoring ──────────────────────────────────────────────────────────────

    def _passes_filters(self, block: dict, query: Query) -> bool:
        if block["id"] in query.exclude_ids:
            return False
        if not query.min_difficulty <= block["difficulty"] <= query.max_difficulty:
            return False
        if query.scenario_tags and not set(query.scenario_tags) & set(block.get("scenario_tags", [])):
            return False
        return True

    def _score(self, block: dict, query: Query) -> float:
        score = 0.0

        if query.text:
            score += self._similarity(block, query.text)

        # Hand-applied tags are a stronger signal than any similarity measure
        # over 226 short sentences, so they are weighted to say so.
        overlap = set(query.scenario_tags) & set(block.get("scenario_tags", []))
        score += 0.5 * len(overlap)

        # The most useful thing a role-play can do is give the learner another
        # go at what they recently got wrong.
        if block.get("intent") in query.error_signature:
            score += 1.0

        return score

    def _similarity(self, block: dict, text: str) -> float:
        embeddings = self._get_embeddings()

        if embeddings is None:
            return _keyword_similarity(
                _tokenise(text), self._tokens[block["id"]], self._document_frequency, len(self.blocks)
            )

        import numpy as np

        query_vector = _embed([text])[0]
        block_vector = embeddings[self._index_of(block["id"])]
        return float(np.dot(query_vector, block_vector))

    @lru_cache(maxsize=1)
    def _index_map(self) -> dict[str, int]:
        return {block["id"]: index for index, block in enumerate(self.blocks)}

    def _index_of(self, block_id: str) -> int:
        return self._index_map()[block_id]

    def _get_embeddings(self):
        """Encode the corpus once, lazily.

        Returns None when `sentence-transformers` is absent, and the keyword
        path takes over. Logged at info, not warning: running without embeddings
        is a supported configuration, not a degradation to be alarmed about.
        """
        if self._embeddings is not None:
            return self._embeddings

        vectors = _embed([block["canonical_text"] for block in self.blocks])
        if vectors is None:
            return None

        self._embeddings = vectors
        return vectors


# ── Embedding backend ────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        log.info(
            "sentence-transformers is not installed; retrieval is using the "
            "keyword path, which is well suited to a hand-tagged corpus of this size"
        )
        return None

    log.info("loading embedding model %s", EMBEDDING_MODEL)
    return SentenceTransformer(EMBEDDING_MODEL)


def _embed(texts: list[str]):
    model = _model()
    if model is None:
        return None
    return model.encode(texts, normalize_embeddings=True)


def embeddings_available() -> bool:
    return _model() is not None


# ── Keyword fallback ─────────────────────────────────────────────────────────


_STOPWORDS = frozenset(
    "a an and are as at be by for from has have i in is it its of on or that "
    "the to was were will with you your".split()
)


def _tokenise(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z']+", text.lower()) if word not in _STOPWORDS}


def _document_frequency(tokens: dict[str, set[str]]) -> dict[str, int]:
    frequency: dict[str, int] = {}
    for token_set in tokens.values():
        for token in token_set:
            frequency[token] = frequency.get(token, 0) + 1
    return frequency


def _keyword_similarity(
    query_tokens: set[str],
    block_tokens: set[str],
    document_frequency: dict[str, int],
    total_documents: int,
) -> float:
    """IDF-weighted overlap.

    Plain overlap counts "please" — which appears in a third of the corpus — as
    heavily as "accommodation", which appears in eight phrases and is the entire
    point of the query. Weighting by inverse document frequency is what makes
    the fallback usable rather than merely present.
    """
    shared = query_tokens & block_tokens
    if not shared:
        return 0.0

    return sum(
        math.log(1 + total_documents / document_frequency.get(token, 1)) for token in shared
    ) / (1 + math.log(1 + len(query_tokens)))


# ── Loading ──────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def load_index() -> PhraseIndex:
    """The index over the built phrase bank.

    Raises rather than returning empty: a GenAI service with no corpus produces
    ungrounded generations, and ungrounded generation is the exact failure this
    whole module exists to prevent. Failing at startup with an actionable
    message beats quietly becoming a chatbot.
    """
    import json
    from pathlib import Path

    for directory in Path(__file__).resolve().parents:
        if (directory / "package.json").exists() and (directory / "packages").is_dir():
            root = directory
            break
    else:  # pragma: no cover - only if the repository layout changes
        raise RuntimeError("Could not locate the repository root from retrieval/index.py")

    path = root / "packages" / "content" / "dist" / "blocks.json"

    if not path.exists():
        raise FileNotFoundError(
            f"Workplace Language Bank not found at {path}.\n"
            "Run `npm run content:build` from the repository root. The GenAI service "
            "cannot ground its generations without the corpus."
        )

    return PhraseIndex(json.loads(path.read_text(encoding="utf-8")))
