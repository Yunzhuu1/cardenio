"""Internal tool registry for deterministic agent orchestration.

Tools are structured backend capabilities called by services or orchestrators.
They are not exposed as public APIs, not MCP tools, and not selected by an LLM
planner.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class Tool(Protocol):
    """Structured internal capability used by deterministic orchestration."""

    name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    async def run(self, input_data: BaseModel) -> BaseModel: ...


class ToolRegistryError(Exception):
    """Base error for tool registry failures."""


class ToolAlreadyRegisteredError(ToolRegistryError):
    """Raised when a tool name is registered more than once."""


class ToolNotFoundError(ToolRegistryError):
    """Raised when a requested tool is not registered."""


class ToolRegistry:
    """Name-based registry for internal tools.

    The registry deliberately does not decide which tool should run. Workflow
    code remains responsible for choosing tools according to product gates.
    """

    def __init__(self, tools: Iterable[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or ():
            self.register(tool)

    def register(self, tool: Tool) -> None:
        """Register a tool by name."""
        _validate_tool_contract(tool)
        if tool.name in self._tools:
            raise ToolAlreadyRegisteredError(
                f"Tool '{tool.name}' is already registered"
            )
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        """Return a registered tool."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool '{name}' is not registered") from exc

    def names(self) -> list[str]:
        """Return registered tool names in stable order."""
        return sorted(self._tools)

    def has(self, name: str) -> bool:
        """Return whether a tool is registered."""
        return name in self._tools


def _validate_tool_contract(tool: Tool) -> None:
    if not tool.name.strip():
        raise ToolRegistryError("Tool name must not be blank")
    if not issubclass(tool.input_model, BaseModel):
        raise ToolRegistryError("Tool input_model must be a Pydantic BaseModel")
    if not issubclass(tool.output_model, BaseModel):
        raise ToolRegistryError("Tool output_model must be a Pydantic BaseModel")
