"""Re-export the generated Pydantic contracts under a stable import path.

Application code imports from `app.contracts`, never from the generated file
directly. That keeps the path to `packages/contracts/generated/models.py` in one
place, so moving or packaging the contracts later touches this file alone.

The generated models are the same shapes the web client uses, produced from the
same JSON Schema. See packages/contracts/README.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

_GENERATED = Path(__file__).resolve().parents[3] / "packages" / "contracts" / "generated"

if not (_GENERATED / "models.py").exists():  # pragma: no cover - setup guard
    raise ImportError(
        f"Generated contracts not found at {_GENERATED}.\n"
        "Run `npm run contracts:build` from the repository root."
    )

if str(_GENERATED) not in sys.path:
    sys.path.insert(0, str(_GENERATED))

from models import (  # noqa: E402
    AssetRef,
    CommunicationAbilityProfile,
    ContentBlock,
    InputMode,
    IslClip,
    LearnerResponse,
    OutputChannel,
    Pictograph,
    SpeechStatus,
    TextComplexity,
)

__all__ = [
    "AssetRef",
    "CommunicationAbilityProfile",
    "ContentBlock",
    "InputMode",
    "IslClip",
    "LearnerResponse",
    "OutputChannel",
    "Pictograph",
    "SpeechStatus",
    "TextComplexity",
]
