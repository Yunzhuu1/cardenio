"""API route aggregation (api.md §2–§13).

Each module handles one resource group following the api.md spec.
"""

from fastapi import APIRouter

from cardenio.api.routes import (
    artifacts,
    auth,
    characters,
    consistency,
    export,
    intent,
    outline,
    projects,
    report,
    screenplay,
    settings,
    source,
    understanding,
)

router = APIRouter()

router.include_router(auth.router, tags=["Auth"])
router.include_router(artifacts.router, tags=["Artifacts"])
router.include_router(projects.router, tags=["Projects"])
router.include_router(source.router, tags=["Source"])
router.include_router(understanding.router, tags=["Understanding"])
router.include_router(characters.router, tags=["Characters"])
router.include_router(intent.router, tags=["Intent"])
router.include_router(outline.router, tags=["Outline"])
router.include_router(screenplay.router, tags=["Screenplay"])
router.include_router(consistency.router, tags=["Consistency"])
router.include_router(report.router, tags=["Report"])
router.include_router(export.router, tags=["Export"])
router.include_router(settings.router, tags=["Settings"])
