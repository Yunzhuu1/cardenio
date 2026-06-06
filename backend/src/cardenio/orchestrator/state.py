"""Project state machine and gate conditions (api.md §2.2, §15.2).

Enforces P1: understand before adapting.  All state transitions and gate
checks are centralized here.  The API layer calls ``check_gate()`` before
any generative action; the orchestrator pipeline calls ``transition()`` after
successful generation.
"""

from __future__ import annotations

from cardenio.domain.models.base import (
    GATE_CONDITIONS,
    VALID_TRANSITIONS,
    ArtifactState,
    ProjectState,
)


class StateGateBlockedError(Exception):
    """Raised when a generative action is blocked by an unmet confirmation gate."""

    def __init__(
        self,
        *,
        action: str,
        required_state: str,
        current_state: str,
        artifact: str,
    ) -> None:
        self.action = action
        self.required_state = required_state
        self.current_state = current_state
        self.artifact = artifact
        msg = (
            f"Action '{action}' blocked: {artifact} must be {required_state}, "
            f"but is {current_state}"
        )
        super().__init__(msg)


class InvalidTransitionError(Exception):
    """Raised when a state transition is not in the valid transitions table."""

    def __init__(self, *, current: ProjectState, target: ProjectState) -> None:
        self.current = current
        self.target = target
        valid = VALID_TRANSITIONS.get(current, set())
        msg = f"Invalid transition: {current.value} → {target.value}. Valid: {valid}"
        super().__init__(msg)


class ChapterThresholdUnmetError(Exception):
    """Raised when source has fewer than 3 chapters (FR-1.3)."""

    def __init__(self, *, current: int, required: int = 3) -> None:
        self.current = current
        self.required = required
        msg = f"Need at least {required} chapters, but only {current} exist"
        super().__init__(msg)


class ProjectStateMachine:
    """Enforces P1: understand before adapting.

    All gate checking lives here.  The state machine is a pure function —
    it reads current state and gates, validates, and returns new state
    without side effects.
    """

    def __init__(
        self,
        current_state: ProjectState,
        gates: dict[str, ArtifactState] | None = None,
    ) -> None:
        self.current_state = current_state
        self.gates = gates or {}

    def can_transition(self, target: ProjectState) -> bool:
        """Check if transitioning to ``target`` is valid from current state."""
        valid_targets = VALID_TRANSITIONS.get(self.current_state, set())
        return target in valid_targets

    def transition(self, target: ProjectState) -> ProjectStateMachine:
        """Attempt a state transition. Raises InvalidTransitionError if invalid."""
        if not self.can_transition(target):
            raise InvalidTransitionError(current=self.current_state, target=target)
        return ProjectStateMachine(target, self.gates)

    def check_gate(self, action: str) -> None:
        """Check whether ``action`` is allowed given current gate states.

        Raises ``StateGateBlockedError`` if any prerequisite is unmet
        (api.md §15.2).
        """
        required = GATE_CONDITIONS.get(action, {})
        for artifact, required_state in required.items():
            current = self.gates.get(artifact)
            if current != required_state:
                raise StateGateBlockedError(
                    action=action,
                    required_state=required_state.value,
                    current_state=current.value if current else "absent",
                    artifact=artifact,
                )
