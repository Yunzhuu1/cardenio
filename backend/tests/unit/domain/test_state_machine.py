"""State machine tests (api.md §2.2, §15.2).

Verifies project state transitions, gate conditions, and blocking behavior.
"""

import pytest

from cardenio.domain.models.base import ArtifactState, ProjectState
from cardenio.orchestrator.state import (
    InvalidTransitionError,
    ProjectStateMachine,
    StateGateBlockedError,
)


class TestProjectStateMachine:
    """ProjectStateMachine enforces P1: understand before adapting."""

    def test_valid_transitions(self) -> None:
        """Transitions follow the api.md §2.2 state machine."""
        sm = ProjectStateMachine(ProjectState.EMPTY)
        assert sm.can_transition(ProjectState.IMPORTED)

        sm2 = ProjectStateMachine(ProjectState.IMPORTED)
        assert sm2.can_transition(ProjectState.UNDERSTOOD)

    def test_invalid_transitions_blocked(self) -> None:
        """Cannot skip states."""
        sm = ProjectStateMachine(ProjectState.EMPTY)
        assert not sm.can_transition(ProjectState.GENERATED)

        sm2 = ProjectStateMachine(ProjectState.IMPORTED)
        assert not sm2.can_transition(ProjectState.OUTLINED)

    def test_transition_returns_new_machine(self) -> None:
        sm = ProjectStateMachine(ProjectState.EMPTY)
        new_sm = sm.transition(ProjectState.IMPORTED)
        assert new_sm.current_state == ProjectState.IMPORTED

    def test_transition_invalid_raises(self) -> None:
        sm = ProjectStateMachine(ProjectState.EMPTY)
        with pytest.raises(InvalidTransitionError):
            sm.transition(ProjectState.GENERATED)

    def test_editing_can_loop(self) -> None:
        """editing ⇄ generated is allowed (api.md §7.1)."""
        sm = ProjectStateMachine(ProjectState.GENERATED)
        editing = sm.transition(ProjectState.EDITING)
        assert editing.current_state == ProjectState.EDITING

        back = editing.transition(ProjectState.GENERATED)
        assert back.current_state == ProjectState.GENERATED


class TestGateConditions:
    """Gate conditions from api.md §15.2."""

    def test_characters_generate_requires_understanding_confirmed(self) -> None:
        """characters:generate is blocked until understanding is confirmed."""
        # understanding not confirmed → blocked
        sm = ProjectStateMachine(
            ProjectState.IMPORTED,
            gates={"understanding": ArtifactState.DRAFT},
        )
        with pytest.raises(StateGateBlockedError):
            sm.check_gate("characters:generate")

    def test_characters_generate_allowed_when_confirmed(self) -> None:
        """characters:generate allowed when understanding IS confirmed."""
        sm = ProjectStateMachine(
            ProjectState.IMPORTED,
            gates={"understanding": ArtifactState.CONFIRMED},
        )
        # Should not raise
        sm.check_gate("characters:generate")

    def test_screenplay_generate_requires_outline_confirmed(self) -> None:
        """screenplay:generate requires outline confirmed."""
        sm = ProjectStateMachine(
            ProjectState.INTENT_SET,
            gates={"outline": ArtifactState.DRAFT},
        )
        with pytest.raises(StateGateBlockedError):
            sm.check_gate("screenplay:generate")

    def test_unknown_action_passes(self) -> None:
        """Unknown actions have no gate conditions (no entry in table)."""
        sm = ProjectStateMachine(ProjectState.EMPTY)
        sm.check_gate("unknown:action")  # should not raise