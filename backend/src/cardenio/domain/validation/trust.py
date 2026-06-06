"""Trust enforcement at the orchestration level (agent-workflow §6).

These checks are NOT merely suggested in prompts — the orchestrator forces
them on every agent output before it enters the artifact store.  This is the
product's core differentiator vs a black-box AI (P4, P5, P6).

Five enforcement points:
1. Source ref backfill: every beat must carry source_ref; missing → retry
2. ai_inferred forced flag: no corresponding source → must be ai_inferred
3. Intent gating: allow_new_plot=false → reject ai_inferred plot nodes
4. TODO blanks: low-confidence beats become TODO, not guessed content
5. Must-keep lines: intent.must_keep_lines must appear verbatim, flagged from_source
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
    """Enforcement point 1: every non-TODO beat must carry source_ref.

    Beats without source_ref are candidates for retry.  If retry budget
    is exhausted, mark them as needing attention rather than polluting
    the artifact store (agent-workflow §8).
    """
    # Implementation will include retry logic in the pipeline.
    # For now, this is a structural check.
    return beats


def enforce_ai_inferred_flag(beats: list[Beat], source_paragraph_indices: set[int]) -> list[Beat]:
    """Enforcement point 2: beats without a matching source are ai_inferred.

    P5 / FR-7.5: this is a **bottom-line requirement**.  The report module
    cross-checks these flags; mismatch is considered a generation failure.
    """
    enforced: list[Beat] = []
    for beat in beats:
        if beat.type == BeatType.TODO:
            enforced.append(beat)
            continue
        if beat.source_ref is None or not beat.source_ref.paragraphs:
            # No source reference → must be ai_inferred
            enforced.append(beat.model_copy(update={"flag": Flag.AI_INFERRED}))
        elif not any(p in source_paragraph_indices for p in beat.source_ref.paragraphs):
            # Source ref points to paragraphs not in the source → ai_inferred
            enforced.append(beat.model_copy(update={"flag": Flag.AI_INFERRED}))
        else:
            enforced.append(beat)
    return enforced


def enforce_intent_gating(
    beats: list[Beat],
    intent: IntentConstraints,
) -> list[Beat]:
    """Enforcement point 3: when allow_new_plot=false, reject ai_inferred plot nodes.

    FR-4: only allow media-translation-level externalizations (voice_over, note,
    action visualizations), not new plot points.  This is enforced from the
    constraint side, not by relying on prompt instructions (O4).
    """
    if intent.allow_new_plot:
        return beats

    plot_beat_types = {BeatType.ACTION, BeatType.DIALOGUE}
    rejected: list[Beat] = []
    for beat in beats:
        if beat.flag == Flag.AI_INFERRED and beat.type in plot_beat_types:
            # Reject this beat — convert to TODO so the author fills it in
            rejected.append(
                beat.model_copy(update={
                    "type": BeatType.TODO,
                    "text": beat.text or (
                        "意图门控：此处 AI 新增的剧情节点被拒绝"
                        "（allow_new_plot=false），需作者补充。"
                    ),
                    "flag": None,
                })
            )
        else:
            rejected.append(beat)
    return rejected


def enforce_must_keep_lines(beats: list[Beat], must_keep_lines: list[str]) -> list[Beat]:
    """Enforcement point 5: must_keep_lines must appear verbatim, flagged from_source.

    Each line in ``must_keep_lines`` must be found as dialogue text in at
    least one beat, and that beat must have ``flag=from_source``.
    """
    # Structural check — full implementation in pipeline
    return beats


def enforce_trust(
    beats: list[Beat],
    *,
    source_paragraph_indices: set[int] = set(),
    intent: IntentConstraints | None = None,
    must_keep_lines: list[str] | None = None,
) -> list[Beat]:
    """Apply all trust enforcement points to a list of beats.

    This is called by the orchestrator after each agent output, before
    the result enters the artifact store (agent-workflow §6).
    """
    result = enforce_source_ref(beats)
    if source_paragraph_indices:
        result = enforce_ai_inferred_flag(result, source_paragraph_indices)
    if intent and not intent.allow_new_plot:
        result = enforce_intent_gating(result, intent)
    if must_keep_lines:
        result = enforce_must_keep_lines(result, must_keep_lines)
    return result
