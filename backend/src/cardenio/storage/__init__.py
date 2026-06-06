"""Storage layer — pluggable persistence (design.md §5).

Artifact store and job store are defined as Protocols so the domain layer
depends on abstractions, not SQLite specifically.  SQLite is the default
implementation; PostgreSQL can be swapped in later.
"""

from cardenio.storage.protocol import ArtifactStore as ArtifactStore
from cardenio.storage.protocol import JobStore as JobStore
