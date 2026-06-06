"""Agent contracts — stateless, idempotent task units (agent-workflow §2-5).

Each agent defines structured I/O types and a ``run()`` coroutine.
The orchestrator calls agents deterministically; agents never decide what to
do next on their own (O1).
"""

from cardenio.domain.agents.base import AgentContext, AgentProtocol, AgentResult

__all__ = ["AgentProtocol", "AgentContext", "AgentResult"]
