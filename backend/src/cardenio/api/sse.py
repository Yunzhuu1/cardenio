"""SSE (Server-Sent Events) streaming helpers (api.md §2.4).

Generation endpoints return 202 with a Job, then stream progress/delta/done/error
events via SSE.  This module provides event formatting utilities.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class SSEEvent:
    """A single SSE event (api.md §2.4)."""

    event: str  # progress | delta | done | error
    data: dict[str, Any]

    def encode(self) -> str:
        """Format as text/event-stream."""
        return f"event: {self.event}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


def progress_event(
    *,
    phase: str,
    done: int,
    total: int,
    scene_id: str | None = None,
) -> SSEEvent:
    """Progress event: how far along a generation job is."""
    data: dict[str, Any] = {"phase": phase, "done": done, "total": total}
    if scene_id:
        data["scene_id"] = scene_id
    return SSEEvent(event="progress", data=data)


def delta_event(
    *,
    path: str,
    text: str,
) -> SSEEvent:
    """Delta event: streaming text for a specific path in the artifact."""
    return SSEEvent(event="delta", data={"path": path, "text": text})


def done_event(*, artifact_version: str) -> SSEEvent:
    """Done event: generation completed successfully."""
    return SSEEvent(event="done", data={"artifact_version": artifact_version})


def error_event(*, code: str, retryable: bool = False, message: str = "") -> SSEEvent:
    """Error event: generation failed."""
    return SSEEvent(
        event="error",
        data={"code": code, "retryable": retryable, "message": message},
    )
