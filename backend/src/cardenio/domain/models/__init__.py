"""Domain models implementing PRD §7 YAML Schema and api.md data contracts.

All models use ``ConfigDict(extra="forbid")`` by default to enforce schema
strictness and guarantee M0-T2 roundtrip losslessness.
"""

from cardenio.domain.models.base import (
    GATE_CONDITIONS,
    VALID_TRANSITIONS,
    ArtifactEnvelope,
    ArtifactState,
    Flag,
    ProjectState,
    SourceRef,
    TrustMixin,
)
from cardenio.domain.models.characters import (
    Character,
    CharacterRelation,
    CharacterRole,
    CharactersData,
)
from cardenio.domain.models.intent import AdaptationDirection, IntentConflict, IntentConstraints
from cardenio.domain.models.outline import (
    IntExt,
    MergeSuggestion,
    MergeSuggestionStatus,
    OutlineData,
    OutlineScene,
    RelationChange,
    SceneHeading,
    TimeOfDay,
)
from cardenio.domain.models.project import GateStatus, LanguageTriplet, ProjectMeta
from cardenio.domain.models.report import (
    ExternalizationEntry,
    ReportData,
    ReportEntry,
    ReviewRecommendation,
)
from cardenio.domain.models.screenplay import (
    Beat,
    BeatOption,
    BeatType,
    ScreenplayData,
    ScreenplayScene,
    ShotHints,
)
from cardenio.domain.models.source import (
    Chapter,
    CreateChapterRequest,
    SourceParagraph,
    SourceStats,
)
from cardenio.domain.models.understanding import Narrative, NonVisualizableMark, UnderstandingData

__all__ = [
    # base
    "Flag",
    "SourceRef",
    "TrustMixin",
    "ArtifactState",
    "ProjectState",
    "ArtifactEnvelope",
    "VALID_TRANSITIONS",
    "GATE_CONDITIONS",
    # project
    "LanguageTriplet",
    "GateStatus",
    "ProjectMeta",
    # source
    "Chapter",
    "CreateChapterRequest",
    "SourceParagraph",
    "SourceStats",
    # understanding
    "UnderstandingData",
    "NonVisualizableMark",
    "Narrative",
    # characters
    "Character",
    "CharacterRole",
    "CharacterRelation",
    "CharactersData",
    # intent
    "IntentConstraints",
    "AdaptationDirection",
    "IntentConflict",
    # outline
    "SceneHeading",
    "IntExt",
    "TimeOfDay",
    "OutlineScene",
    "RelationChange",
    "MergeSuggestion",
    "MergeSuggestionStatus",
    "OutlineData",
    # screenplay
    "BeatType",
    "BeatOption",
    "Beat",
    "ScreenplayScene",
    "ShotHints",
    "ScreenplayData",
    # report
    "ReportEntry",
    "ExternalizationEntry",
    "ReviewRecommendation",
    "ReportData",
]
