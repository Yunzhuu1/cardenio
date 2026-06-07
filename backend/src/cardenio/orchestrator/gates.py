"""Internal generation gatekeeper for artifact confirmation checks."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.orchestrator.state import ProjectStateMachine, StateGateBlockedError

_GATE_MESSAGES = {
    "characters:generate": "Understanding must be confirmed before generating characters",
    "outline:generate": "Characters must be confirmed before generating outline",
    "screenplay:generate": "Outline must be confirmed before generating screenplay",
}


def generation_gate_response(
    action: str,
    artifacts: dict[str, ArtifactEnvelope[Any] | None],
) -> JSONResponse | None:
    """Return a 409 response if an internal generation gate blocks the action."""
    gates = {
        artifact_type: artifact.state
        for artifact_type, artifact in artifacts.items()
        if artifact is not None
    }
    try:
        ProjectStateMachine(ProjectState.EMPTY, gates).check_gate(action)
    except StateGateBlockedError as exc:
        return _gate_error_response(exc)
    return None


def _gate_error_response(exc: StateGateBlockedError) -> JSONResponse:
    current_state = exc.current_state
    if current_state == "absent":
        current_state = "empty"
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "state_gate_blocked",
                "message": _GATE_MESSAGES[exc.action],
                "retryable": False,
                "details": {
                    "artifact": exc.artifact,
                    "required_state": ArtifactState.CONFIRMED.value,
                    "current_state": current_state,
                },
            }
        },
    )
