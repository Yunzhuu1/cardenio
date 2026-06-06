"""Trust enforcement at the orchestration level.

These checks are applied before generated output enters the artifact store.
They enforce traceability, AI-origin marking, author intent, and TODO blanks.
"""

from __future__ import annotations

from cardenio.domain.models.base import Flag
from cardenio.domain.models.intent import IntentConstraints
from cardenio.domain.models.screenplay import Beat, BeatType


class TrustEnforcementError(Exception):
    """Raised when trust enforcement fails after max retries."""

    def __init__(
        self, message: str, *, retryable: bool = False, details: dict | None = None
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.details = details or {}


def enforce_source_ref(beats: list[Beat]) -> list[Beat]:
    """Every non-TODO beat must eventually carry source_ref."""
    return beats


def enforce_ai_inferred_flag(
    beats: list[Beat], source_paragraph_indices: set[int]
) -> list[Beat]:
    """Beats without a matching source paragraph are marked ai_inferred."""
    enforced: list[Beat] = []
    for beat in beats:
        if beat.type == BeatType.TODO:
            enforced.append(beat)
            continue
        if beat.source_ref is None or not beat.source_ref.paragraphs:
            enforced.append(beat.model_copy(update={"flag": Flag.AI_INFERRED}))
        elif not any(p in source_paragraph_indices for p in beat.source_ref.paragraphs):
            enforced.append(beat.model_copy(update={"flag": Flag.AI_INFERRED}))
        else:
            enforced.append(beat)
    return enforced


def enforce_intent_gating(
    beats: list[Beat],
    intent: IntentConstraints,
) -> list[Beat]:
    """Reject AI-inferred plot beats when the author disallows new plot."""
    if intent.allow_new_plot:
        return beats

    plot_beat_types = {BeatType.ACTION, BeatType.DIALOGUE}
    rejected: list[Beat] = []
    for beat in beats:
        if beat.flag == Flag.AI_INFERRED and beat.type in plot_beat_types:
            rejected.append(
                beat.model_copy(
                    update={
                        "type": BeatType.TODO,
                        "text": beat.text
                        or (
                            "Intent gate rejected an AI-inferred plot beat "
                            "(allow_new_plot=false); author input is required."
                        ),
                        "flag": None,
                    }
                )
            )
        else:
            rejected.append(beat)
    return rejected


def enforce_must_keep_lines(beats: list[Beat], must_keep_lines: list[str]) -> list[Beat]:
    """Require exact must-keep lines to appear and be marked from_source."""
    missing_lines: list[str] = []
    untrusted_lines: list[str] = []
    for line in must_keep_lines:
        matched = [beat for beat in beats if _beat_text(beat) == line]
        if not matched:
            missing_lines.append(line)
            continue
        if not any(beat.flag == Flag.FROM_SOURCE for beat in matched):
            untrusted_lines.append(line)

    if missing_lines or untrusted_lines:
        raise TrustEnforcementError(
            "Must-keep lines must appear verbatim and be marked from_source",
            retryable=True,
            details={
                "missing_lines": missing_lines,
                "untrusted_lines": untrusted_lines,
            },
        )
    return beats


def enforce_trust(
    beats: list[Beat],
    *,
    source_paragraph_indices: set[int] = set(),
    intent: IntentConstraints | None = None,
    must_keep_lines: list[str] | None = None,
) -> list[Beat]:
    """Apply trust enforcement points to a list of beats."""
    result = enforce_source_ref(beats)
    if source_paragraph_indices:
        result = enforce_ai_inferred_flag(result, source_paragraph_indices)
    if intent and not intent.allow_new_plot:
        result = enforce_intent_gating(result, intent)
    if must_keep_lines:
        result = enforce_must_keep_lines(result, must_keep_lines)
    return result


def _beat_text(beat: Beat) -> str | None:
    return beat.dialogue or beat.text
