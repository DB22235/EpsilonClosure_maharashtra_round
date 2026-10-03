"""
API v1 root router aggregator.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import routes_admin, routes_auth, routes_campaigns, routes_public_campaigns
from app.config import lru_settings

api_router = APIRouter(prefix=lru_settings().API_V1_PREFIX)

# Mount domain route modules
api_router.include_router(routes_auth.router)
api_router.include_router(routes_public_campaigns.router)
api_router.include_router(routes_campaigns.router)
api_router.include_router(routes_admin.router)

# Alias for backwards compatibility
v1_router = api_router
