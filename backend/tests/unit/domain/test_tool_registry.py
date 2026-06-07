"""Tool registry tests."""

import pytest
from pydantic import BaseModel

from cardenio.domain.tools import (
    ToolAlreadyRegisteredError,
    ToolNotFoundError,
    ToolRegistry,
    ToolRegistryError,
)


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    text: str


class EchoTool:
    name = "test.echo"
    input_model = EchoInput
    output_model = EchoOutput

    async def run(self, input_data: BaseModel) -> BaseModel:
        payload = EchoInput.model_validate(input_data)
        return EchoOutput(text=payload.text)


class BlankNameTool(EchoTool):
    name = " "


class InvalidInputModelTool(EchoTool):
    input_model = dict


class InvalidOutputModelTool(EchoTool):
    output_model = dict


async def test_registry_registers_and_returns_tool() -> None:
    tool = EchoTool()
    registry = ToolRegistry()

    registry.register(tool)

    assert registry.has("test.echo") is True
    assert registry.names() == ["test.echo"]
    assert registry.get("test.echo") is tool
    result = await registry.get("test.echo").run(EchoInput(text="hello"))
    assert result == EchoOutput(text="hello")


def test_registry_accepts_initial_tools() -> None:
    registry = ToolRegistry([EchoTool()])

    assert registry.names() == ["test.echo"]


def test_registry_rejects_duplicate_tool_names() -> None:
    registry = ToolRegistry([EchoTool()])

    with pytest.raises(ToolAlreadyRegisteredError):
        registry.register(EchoTool())


def test_registry_rejects_unknown_tool() -> None:
    registry = ToolRegistry()

    with pytest.raises(ToolNotFoundError):
        registry.get("missing.tool")


@pytest.mark.parametrize(
    "tool",
    [BlankNameTool(), InvalidInputModelTool(), InvalidOutputModelTool()],
)
def test_registry_validates_tool_contract(tool: EchoTool) -> None:
    registry = ToolRegistry()

    with pytest.raises(ToolRegistryError):
        registry.register(tool)
