"""FastAPI application layer (design.md §2, api.md).

The API layer is thin: parse request, call domain/orchestrator, serialize
response.  No business logic lives here.
"""

from cardenio.api.app import create_app as create_app
