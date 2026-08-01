"""Feature flags, for the client (Blueprint F6).

One request, at boot, returning every flag's state for this learner. Not one
request per flag: a learner on a poor connection would otherwise assemble a
half-configured interface out of several round trips, showing the new level
runner with the old navigation.

The client is told **what is on for them**, never the registry — rollout
percentages and descriptions are operator information, and a learner who can
read "game_loop: 10%" learns they are in an experiment they were not asked
about.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from samvaad_platform.flags import all_for

from app.security.auth import CurrentUser

router = APIRouter(prefix="/flags", tags=["flags"])


class FlagsOut(BaseModel):
    #: name -> on for this learner.
    flags: dict[str, bool]


@router.get("", response_model=FlagsOut, summary="Which features are on for me")
async def my_flags(principal: CurrentUser) -> FlagsOut:
    # Bucketing is by user id, so the answer is stable for a learner across
    # requests and across deploys. An interface that changes underneath somebody
    # mid-session is, for a learner with a cognitive disability, a different app
    # than the one they opened.
    return FlagsOut(flags=all_for(principal.user_id))
