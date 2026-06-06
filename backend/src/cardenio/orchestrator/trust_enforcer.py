"""Trust enforcement at the pipeline level (agent-workflow §6).

The orchestrator applies these checks AFTER each agent call and BEFORE
writing results to the artifact store.  This is the product's core
differentiator vs a black-box AI (P4, P5, P6).

These functions wrap the domain-level trust checks in
``cardenio.domain.validation.trust`` with pipeline context (intent, source
bounds, etc.).
"""

from __future__ import annotations

from cardenio.domain.models.intent import IntentConstraints
from cardenio.domain.models.screenplay import Beat, ScreenplayScene
from cardenio.domain.validation.trust import enforce_trust


def enforce_pipeline_trust(
    scenes: list[ScreenplayScene],
    *,
    source_paragraph_indices: set[int] | None = None,
    intent: IntentConstraints | None = None,
    must_keep_lines: list[str] | None = None,
) -> list[ScreenplayScene]:
    """Apply trust enforcement to all scenes in a screenplay artifact.

    This is called by the pipeline after scene agent output, before the
    result enters the artifact store (agent-workflow §6).
    """
    enforced_scenes: list[ScreenplayScene] = []
    for scene in scenes:
        enforced_beats: list[Beat] = enforce_trust(
            scene.beats,
            source_paragraph_indices=source_paragraph_indices or set(),
            intent=intent,
            must_keep_lines=must_keep_lines,
        )
        enforced_scenes.append(scene.model_copy(update={"beats": enforced_beats}))
    return enforced_scenes
