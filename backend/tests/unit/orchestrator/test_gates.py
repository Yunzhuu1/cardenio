"""Generation gatekeeper tests."""

from __future__ import annotations

from typing import Any

import pytest

from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState
from cardenio.orchestrator.gates import generation_gate_response


@pytest.mark.parametrize(
    ("action", "artifact_type", "message"),
    [
        (
            "characters:generate",
            "understanding",
            "Understanding must be confirmed before generating characters",
        ),
        (
            "outline:generate",
            "characters",
            "Characters must be confirmed before generating outline",
        ),
        (
            "screenplay:generate",
            "outline",
            "Outline must be confirmed before generating screenplay",
        ),
    ],
)
def test_generation_gate_response_blocks_missing_artifact(
    action: str,
    artifact_type: str,
    message: str,
) -> None:
    response = generation_gate_response(action, {artifact_type: None})

    assert response is not None
    assert response.status_code == 409
    assert response.body
    body = response.body.decode()
    assert "state_gate_blocked" in body
    assert message in body
    assert f'"artifact":"{artifact_type}"' in body
    assert '"required_state":"confirmed"' in body
    assert '"current_state":"empty"' in body


def test_generation_gate_response_blocks_wrong_state() -> None:
    artifact = _artifact("characters", state=ArtifactState.NEEDS_RECOMPUTE)

    response = generation_gate_response("outline:generate", {"characters": artifact})

    assert response is not None
    assert response.status_code == 409
    assert response.body
    assert '"current_state":"needs_recompute"' in response.body.decode()


def test_generation_gate_response_allows_confirmed_artifact() -> None:
    artifact = _artifact("outline", state=ArtifactState.CONFIRMED)

    response = generation_gate_response("screenplay:generate", {"outline": artifact})

    assert response is None


def _artifact(
    artifact_type: str,
    *,
    state: ArtifactState,
) -> ArtifactEnvelope[Any]:
    return ArtifactEnvelope(
        type=artifact_type,
        state=state,
        data={},
    )
