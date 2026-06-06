"""Middleware — auth, i18n Accept-Language, error handling (api.md §1.2, §1.3)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from cardenio.api.errors import ERROR_STATUS_MAP, CardenioError


async def cardenio_error_handler(request: Request, exc: CardenioError) -> JSONResponse:
    """Convert CardenioError to JSON error response (api.md §1.6)."""
    status_code = ERROR_STATUS_MAP.get(type(exc), 500)
    return JSONResponse(status_code=status_code, content=exc.to_dict())


def get_ui_language(request: Request) -> str:
    """Determine UI language from Accept-Language header (NFR-7).

    Defaults to zh-CN.  The server never assumes UI language equals
    source or output language.
    """
    accept_language = request.headers.get("accept-language", "zh-CN")
    # Simplified: take the first language in the header
    # Full implementation would parse quality values
    lang = accept_language.split(",")[0].split(";")[0].strip()
    return lang if lang else "zh-CN"
