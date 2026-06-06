"""Agent contract shape tests (agent-workflow §3-5).

Each agent module must define a task_name and an async run() method.
"""

import pytest

from cardenio.domain.agents.base import AgentContext, AgentProtocol
from cardenio.domain.agents import preprocess, understand, profile, intent_compile
from cardenio.domain.agents import outline, scene, consistency, report, rewrite


AGENT_MODULES = [
    ("preprocess", preprocess.PreprocessAgent),
    ("understand", understand.UnderstandAgent),
    ("profile", profile.ProfileAgent),
    ("intent", intent_compile.IntentCompileAgent),
    ("outline", outline.OutlineAgent),
    ("scene", scene.SceneAgent),
    ("consistency", consistency.ConsistencyAgent),
    ("report", report.ReportAgent),
    ("rewrite", rewrite.RewriteAgent),
]


@pytest.mark.parametrize("task_name,agent_cls", AGENT_MODULES)
async def test_agent_has_task_name(task_name: str, agent_cls: type) -> None:
    """Each agent must have a task_name matching agent-workflow §3."""
    agent = agent_cls()
    assert agent.task_name == task_name


@pytest.mark.parametrize("task_name,agent_cls", AGENT_MODULES)
async def test_agent_has_run_method(task_name: str, agent_cls: type) -> None:
    """Each agent must expose an async run() method."""
    agent = agent_cls()
    assert hasattr(agent, "run")
    assert callable(agent.run)


@pytest.mark.parametrize("task_name,agent_cls", AGENT_MODULES)
async def test_agent_run_raises_not_implemented(task_name: str, agent_cls: type) -> None:
    """M0 skeleton agents raise NotImplementedError until milestone implementation."""
    agent = agent_cls()
    context = AgentContext()
    with pytest.raises(NotImplementedError):
        await agent.run(context)