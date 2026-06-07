"""Consistency API (api.md API-23)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator

from cardenio.api.deps import get_artifact_store
from cardenio.domain.models.base import ArtifactEnvelope, ProjectState
from cardenio.domain.models.characters import CharactersData
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/consistency")

TEXT_RENAME_SKIP_KEYS = {
    "character",
    "characters",
    "flag",
    "id",
    "role",
    "source_ref",
    "to",
    "type",
}

OPTIONAL_RENAME_ARTIFACTS = ("outline", "screenplay", "report")


class RenameCharacterRequest(BaseModel):
    """Request body for deterministic global character rename."""

    model_config = ConfigDict(extra="forbid")

    character_id: str
    new_name: str
    confirm: bool = False

    @field_validator("character_id", "new_name")
    @classmethod
    def value_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be blank")
        return stripped


@router.post(":rename")
async def rename_character(
    project_id: str,
    body: RenameCharacterRequest,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-23: Global character rename (deterministic, FR-9.4)."""
    if not body.confirm:
        raise HTTPException(status_code=409, detail="Rename requires confirm=true")

    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    characters_artifact = await store.get_artifact(project_id, "characters")
    if characters_artifact is None:
        raise HTTPException(status_code=404, detail="Characters not found")

    characters = CharactersData.model_validate(characters_artifact.data)
    data = characters.model_dump(mode="json")
    old_name = _rename_character_profile(data, body.character_id, body.new_name)
    profile_replacements = _replace_text_values(
        data,
        old_name,
        body.new_name,
        skip_keys={*(TEXT_RENAME_SKIP_KEYS - {"characters"}), "name"},
    )
    saved = await _save_artifact_data(store, project_id, characters_artifact, data)
    changed_artifacts = [
        {
            "type": "characters",
            "version": saved.version,
            "replacements": profile_replacements + int(old_name != body.new_name),
        }
    ]

    for artifact_type in OPTIONAL_RENAME_ARTIFACTS:
        artifact = await store.get_artifact(project_id, artifact_type)
        if artifact is None:
            continue
        artifact_data = artifact.data
        replacements = _replace_text_values(artifact_data, old_name, body.new_name)
        if replacements == 0:
            continue
        saved_optional = await _save_artifact_data(
            store, project_id, artifact, artifact_data
        )
        changed_artifacts.append(
            {
                "type": artifact_type,
                "version": saved_optional.version,
                "replacements": replacements,
            }
        )

    if project["state"] != ProjectState.EDITING:
        await store.update_project_state(project_id, ProjectState.EDITING)

    return {
        "character_id": body.character_id,
        "old_name": old_name,
        "new_name": body.new_name,
        "changed_artifacts": changed_artifacts,
        "count": len(changed_artifacts),
    }


@router.post(":check")
async def check_consistency(project_id: str) -> dict:
    """API-23: Detect character consistency conflicts."""
    raise NotImplementedError("Consistency check not yet implemented")


def _rename_character_profile(
    data: dict[str, Any],
    character_id: str,
    new_name: str,
) -> str:
    for character in data["characters"]:
        if character["id"] == character_id:
            old_name = character["name"]
            character["name"] = new_name
            return old_name
    raise HTTPException(status_code=404, detail="Character not found")


def _replace_text_values(
    value: Any,
    old: str,
    new: str,
    *,
    skip_keys: set[str] | None = None,
) -> int:
    if not old or old == new:
        return 0
    if isinstance(value, dict):
        replacements = 0
        skip = skip_keys or TEXT_RENAME_SKIP_KEYS
        for key, item in value.items():
            if key in skip:
                continue
            if isinstance(item, str):
                count = item.count(old)
                if count:
                    value[key] = item.replace(old, new)
                    replacements += count
                continue
            replacements += _replace_text_values(item, old, new, skip_keys=skip)
        return replacements
    if isinstance(value, list):
        replacements = 0
        for index, item in enumerate(value):
            if isinstance(item, str):
                count = item.count(old)
                if count:
                    value[index] = item.replace(old, new)
                    replacements += count
                continue
            replacements += _replace_text_values(item, old, new, skip_keys=skip_keys)
        return replacements
    return 0


async def _save_artifact_data(
    store: SqliteArtifactStore,
    project_id: str,
    previous: ArtifactEnvelope[Any],
    data: dict[str, Any],
) -> ArtifactEnvelope[Any]:
    envelope = ArtifactEnvelope[dict[str, Any]](
        type=previous.type,
        state=previous.state,
        parent_version=previous.version,
        needs_recompute=previous.needs_recompute,
        data=data,
    )
    return await store.save_artifact(project_id, envelope)
