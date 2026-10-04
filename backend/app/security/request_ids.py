"""
Request trace identification utilities.
"""

from __future__ import annotations

import uuid

from fastapi import Request

from app.config import lru_settings


async def get_request_id(request: Request) -> str:
    """
    Extract the request ID from the incoming HTTP header, or generate a fresh one.
    Stores the resolved ID on request.state.request_id.
    """
    # If already computed on this request, reuse it
    if hasattr(request.state, "request_id") and request.state.request_id:
        return str(request.state.request_id)

    settings = lru_settings()
    header_val = request.headers.get(settings.REQUEST_ID_HEADER)

    if header_val and header_val.strip():
        req_id = header_val.strip()
    else:
        req_id = f"req_{uuid.uuid4().hex[:16]}"

    request.state.request_id = req_id
    return req_id
