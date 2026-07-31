"""Cross-language contract agreement.

The same fixtures that `packages/contracts` validates with Ajv are parsed here
with the generated Pydantic models. If the two ever disagree, the schema and one
of the two generators have drifted and the bug would otherwise surface as a
confusing runtime mismatch between the client and the API.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts import CommunicationAbilityProfile, ContentBlock, LearnerResponse

FIXTURES = Path(__file__).resolve().parents[3] / "packages" / "contracts" / "fixtures"

CASES = [
    (ContentBlock, "content-block"),
    (LearnerResponse, "learner-response"),
    (CommunicationAbilityProfile, "communication-ability-profile"),
]


def _load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    # Fixtures carry `_comment` explaining their purpose; not part of the contract.
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _fixture_files(kind: str, bucket: str) -> list[Path]:
    directory = FIXTURES / bucket / kind
    return sorted(directory.glob("*.json")) if directory.exists() else []


@pytest.mark.parametrize(
    ("model", "path"),
    [(m, p) for m, kind in CASES for p in _fixture_files(kind, "valid")],
    ids=lambda v: v.name if isinstance(v, Path) else "",
)
def test_valid_fixtures_parse(model: type, path: Path) -> None:
    model.model_validate(_load(path))


@pytest.mark.parametrize(
    ("model", "path"),
    [(m, p) for m, kind in CASES for p in _fixture_files(kind, "invalid")],
    ids=lambda v: v.name if isinstance(v, Path) else "",
)
def test_invalid_fixtures_are_rejected(model: type, path: Path) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(_load(path))


def test_at_least_one_fixture_per_contract_exists() -> None:
    """Guards against the parametrised tests silently passing on an empty set."""
    for _, kind in CASES:
        assert _fixture_files(kind, "valid"), f"no valid fixtures for {kind}"
