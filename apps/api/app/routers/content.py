"""Serving the Workplace Language Bank (M15).

Until now the client imported the built corpus directly, which inlined all 226
blocks into the JavaScript bundle — around 270 kB raw before ISL and phoneme
data grow it further. Our learners are on entry-level Android and low bandwidth,
so shipping the whole curriculum up front is exactly the wrong trade.

Now the client fetches it once and keeps it in IndexedDB. `ETag` plus a version
means the second visit costs a single 304, and an offline visit costs nothing at
all.

NO AUTHENTICATION HERE, DELIBERATELY
------------------------------------
The phrase bank is curriculum, not learner data. Requiring a token would mean a
learner cannot precache lessons before signing in, and would put an auth check
on the one resource a service worker most wants to fetch eagerly. Nothing here
is personal; everything personal is behind `CurrentUser` elsewhere.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache

from fastapi import APIRouter, Header, Response, status

from app.learning.content import load_blocks

router = APIRouter(prefix="/content", tags=["content"])

#: A day. The ETag makes revalidation cheap, and the corpus changes on deploy,
#: not on a schedule — so this is about how often we are willing to be stale,
#: not about how often it changes.
CACHE_SECONDS = 86_400


@lru_cache(maxsize=1)
def _payload() -> tuple[str, str]:
    """The serialised bank and its ETag, computed once per process."""
    blocks = load_blocks()
    body = json.dumps({"version": _version(blocks), "blocks": blocks}, separators=(",", ":"))
    etag = hashlib.sha256(body.encode()).hexdigest()[:32]
    return body, etag


def _version(blocks: list[dict]) -> str:
    """A content hash, not a build timestamp.

    A timestamp would invalidate every learner's cache on every deploy even when
    the curriculum had not changed — which on a slow connection is a real cost
    paid for nothing.
    """
    digest = hashlib.sha256()
    for block in blocks:
        digest.update(block["id"].encode())
        digest.update(str(block.get("version", 1)).encode())
        digest.update(block["canonical_text"].encode())
    return digest.hexdigest()[:16]


@router.get("/blocks", summary="The whole phrase bank")
async def blocks(
    response: Response,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
) -> Response:
    body, etag = _payload()

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = f"public, max-age={CACHE_SECONDS}"

    if if_none_match == etag:
        # The client already has this exact corpus. Cheapest possible answer.
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=dict(response.headers))

    return Response(content=body, media_type="application/json", headers=dict(response.headers))


@router.get("/version", summary="Just the version")
async def version() -> dict:
    """Lets a client decide whether to re-download without pulling the payload.

    On a metered connection the difference between a 40-byte check and a 270 kB
    download is the difference between checking and not bothering.
    """
    _, etag = _payload()
    return {"version": _version(load_blocks()), "etag": etag, "count": len(load_blocks())}
