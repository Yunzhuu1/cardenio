"""Character profile domain models (api.md §6, FR-3)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CharacterRole(StrEnum):
    """FR-3.1 character classification."""

    PROTAGONIST = "protagonist"
    SUPPORTING = "supporting"
    MENTIONED = "mentioned"


class CharacterRelation(BaseModel):
    """A relationship between this character and another."""

    to: str  # character id
    type: str  # e.g. "父女", "colleague"
    change: str | None = None  # e.g. "由疏离到和解"


class Character(BaseModel):
    """A single character profile (FR-3).

    ``voice`` and ``hard_rules`` become hard constraints for dialogue generation
    once confirmed by the author (agent-workflow §5.2).
    """

    model_config = ConfigDict(extra="forbid")

    id: str  # e.g. "lin_wan"
    name: str
    role: CharacterRole
    voice: str  # speaking style fingerprint (NFR-2)
    desire: str
    fear: str
    arc: str | None = None
    relations: list[CharacterRelation] = []
    hard_rules: list[str] = []  # inviolable character rules (FR-3)


class CharactersData(BaseModel):
    """Characters artifact data (api.md §6)."""

    model_config = ConfigDict(extra="forbid")

    characters: list[Character]
