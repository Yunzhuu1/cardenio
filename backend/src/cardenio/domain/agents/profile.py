"""Profile agent — character extraction (FR-3).

Produces character profiles with voice, hard_rules, relations, arc.
``voice`` and ``hard_rules`` become hard constraints for dialogue generation
once confirmed (agent-workflow §5.2).
"""

from __future__ import annotations

from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext, AgentIssue, ControlledAgent
from cardenio.domain.models.characters import CharactersData
from cardenio.gateway.protocol import LlmGateway


class ProfileAgent(ControlledAgent):
    """Extract character profiles from source (FR-3, agent-workflow §5.2)."""

    task_name = "profile"
    output_model = CharactersData

    def __init__(self, gateway: LlmGateway | None = None) -> None:
        self._enabled = gateway is not None
        if gateway is not None:
            super().__init__(gateway)

    async def run(self, context: AgentContext):
        if not self._enabled:
            raise NotImplementedError("ProfileAgent.run() not yet implemented")
        return await super().run(context)

    def validate_domain(
        self,
        data: BaseModel,
        context: AgentContext,
    ) -> list[AgentIssue]:
        profiles = CharactersData.model_validate(data)
        issues: list[AgentIssue] = []
        if not profiles.characters:
            issues.append(
                AgentIssue(
                    code="empty_character_profiles",
                    message="at least one character profile is required",
                    path="characters",
                )
            )
            return issues

        for index, character in enumerate(profiles.characters):
            required_strings = {
                "id": character.id,
                "name": character.name,
                "voice": character.voice,
                "desire": character.desire,
                "fear": character.fear,
                "role": character.role.value,
            }
            if character.arc is not None:
                required_strings["arc"] = character.arc
            for field, value in required_strings.items():
                if not value.strip():
                    issues.append(
                        AgentIssue(
                            code="blank_character_field",
                            message=f"{field} must not be blank",
                            path=f"characters.{index}.{field}",
                        )
                    )
            if not any(rule.strip() for rule in character.hard_rules):
                issues.append(
                    AgentIssue(
                        code="missing_character_hard_rules",
                        message="at least one hard rule is required",
                        path=f"characters.{index}.hard_rules",
                    )
                )
        return issues
