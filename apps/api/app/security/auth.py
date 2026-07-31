"""Who is asking.

THE HOLE THIS CLOSES
--------------------
Until now every endpoint took `user_id` from the request body. That is an
insecure-direct-object-reference: anyone could read anyone's rehearsed interview
answers, their consent record or their progress by guessing an id.

For this product that is not an abstract severity rating. The data is a disabled
person's practice attempts at disclosing their disability to an employer. It is
close to the most sensitive thing they could give us.

The rule from here on: **identity comes from the token, never from the body.**
`user_id` has been removed from every request model, so it cannot be passed even
by accident.

GUEST FIRST
-----------
A learner can start with no account at all. Someone deciding whether to trust us
should be able to practise saying "good morning" before handing over an email —
and for a disabled learner weighing up who gets to know about their disability,
that is not a small thing. A guest is a real user row with a real token; signing
up later upgrades the row in place, so nothing is lost.

WHAT THIS IS NOT
----------------
Not a full identity provider. There are no passwords here, deliberately: storing
them is a liability we do not need when Supabase Auth (magic links, OAuth) is
already the plan (ADR-0005). This issues and verifies our own short-lived
tokens, and Supabase slots in behind `authenticate` without the routers
changing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

log = logging.getLogger("samvaad.api.auth")

ALGORITHM = "HS256"

#: Long enough that a learner is not signed out mid-interview, short enough that
#: a leaked token is not useful for long. Sessions are refreshed on use.
TOKEN_TTL = timedelta(days=7)

#: `auto_error=False` so a missing token reaches our own handler and produces a
#: message written for a learner, rather than FastAPI's bare "Not authenticated".
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    """The authenticated caller."""

    user_id: str
    role: str = "learner"
    is_guest: bool = True

    @property
    def is_trainer(self) -> bool:
        return self.role in ("trainer", "admin")


class AuthError(HTTPException):
    def __init__(self, message: str) -> None:
        super().__init__(
            status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthenticated", "message": message},
            headers={"WWW-Authenticate": "Bearer"},
        )


def new_user_id(guest: bool = True) -> str:
    return f"{'gst' if guest else 'usr'}_{uuid4().hex[:16]}"


def issue_token(user_id: str, role: str = "learner", is_guest: bool = True) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "guest": is_guest,
            "iat": now,
            "exp": now + TOKEN_TTL,
            "iss": settings.service_name,
        },
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> Principal:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            issuer=settings.service_name,
            options={"require": ["sub", "exp", "iss"]},
        )
    except jwt.ExpiredSignatureError as error:
        raise AuthError("Your session has ended. Please sign in again.") from error
    except jwt.InvalidTokenError as error:
        # Deliberately the same message as expiry: distinguishing "malformed"
        # from "expired" tells an attacker which of the two they achieved.
        raise AuthError("Your session has ended. Please sign in again.") from error

    return Principal(
        user_id=claims["sub"],
        role=claims.get("role", "learner"),
        is_guest=bool(claims.get("guest", True)),
    )


async def authenticate(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    """FastAPI dependency. The only way a route learns who is calling."""
    if credentials is None or not credentials.credentials:
        raise AuthError("Please sign in to continue.")
    return decode_token(credentials.credentials)


CurrentUser = Annotated[Principal, Depends(authenticate)]


async def require_trainer(principal: CurrentUser) -> Principal:
    """For surfaces that show more than one learner's data (M14)."""
    if not principal.is_trainer:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "This part is for trainers."},
        )
    return principal


TrainerUser = Annotated[Principal, Depends(require_trainer)]
