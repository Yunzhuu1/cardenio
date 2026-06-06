"""LLM Gateway abstraction (design.md §6.1).

The gateway is the ONLY interface business code uses to call LLMs.
Provider-specific details never leak upstream — the domain layer only
sees validated, structured data.
"""

from cardenio.gateway.protocol import GenerateRequest, GenerateResult, LlmGateway

__all__ = ["LlmGateway", "GenerateRequest", "GenerateResult"]
