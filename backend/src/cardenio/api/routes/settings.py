"""Settings & privacy API (api.md §13, API-29)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator

from cardenio.api.deps import get_artifact_store
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/settings")


DATA_STORAGE_NOTICE = (
    "Project source text, generated artifacts, and settings are stored in the "
    "configured Cardenio SQLite database for this backend environment."
)
TRAINING_NOTICE = (
    "Cardenio does not use project data for model training. The MVP keeps this "
    "setting locked off so unpublished manuscripts are not treated as training data."
)
LOCAL_PROCESSING_NOTICE = (
    "The architecture keeps provider access behind the backend gateway and reserves "
    "a local/private processing path for deployments that require it."
)


class ProjectSettings(BaseModel):
    """Project-level privacy, language, and generation settings."""

    model_config = ConfigDict(extra="forbid")

    ui_language: str = "zh-CN"
    source_language: str = "zh-CN"
    output_language: str = "zh-CN"
    data_storage_location: Literal["configured_sqlite_database"] = (
        "configured_sqlite_database"
    )
    data_storage_notice: str = DATA_STORAGE_NOTICE
    allow_model_training: bool = False
    training_notice: str = TRAINING_NOTICE
    local_processing_reserved: bool = True
    local_processing_notice: str = LOCAL_PROCESSING_NOTICE
    shot_hints_enabled: bool = False

    @field_validator("allow_model_training")
    @classmethod
    def training_must_remain_disabled(cls, value: bool) -> bool:
        if value:
            raise ValueError("Project data cannot be enabled for model training")
        return value


@router.get("")
async def get_settings(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-29: Get project settings (privacy, shot hints, language)."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "settings")
    if artifact is not None:
        return artifact.model_dump(mode="json")

    return {
        "type": "settings",
        "state": ArtifactState.CONFIRMED.value,
        "version": None,
        "parent_version": None,
        "data": _default_settings(project).model_dump(mode="json"),
    }


@router.put("")
async def update_settings(
    project_id: str,
    body: ProjectSettings,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-29: Update project settings."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "settings")
    data = _normalize_settings(body)
    await store.update_project_meta(
        project_id,
        {
            "ui_language": data.ui_language,
            "source_language": data.source_language,
            "output_language": data.output_language,
        },
    )
    envelope = ArtifactEnvelope[ProjectSettings](
        type="settings",
        state=ArtifactState.CONFIRMED,
        parent_version=previous.version if previous else None,
        data=data,
    )
    saved = await store.save_artifact(project_id, envelope)
    return saved.model_dump(mode="json")


def _default_settings(project: dict) -> ProjectSettings:
    return ProjectSettings(
        ui_language=project["ui_language"],
        source_language=project["source_language"],
        output_language=project["output_language"],
    )


def _normalize_settings(settings: ProjectSettings) -> ProjectSettings:
    return settings.model_copy(
        update={
            "data_storage_location": "configured_sqlite_database",
            "data_storage_notice": DATA_STORAGE_NOTICE,
            "allow_model_training": False,
            "training_notice": TRAINING_NOTICE,
            "local_processing_reserved": True,
            "local_processing_notice": LOCAL_PROCESSING_NOTICE,
        }
    )
