"""
API v1 root router aggregator.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    routes_admin,
    routes_audit,
    routes_auth,
    routes_campaigns,
    routes_challenges,
    routes_entitlements,
    routes_metrics,
    routes_public_campaigns,
    routes_registration,
)
from app.config import lru_settings

api_router = APIRouter(prefix=lru_settings().API_V1_PREFIX)

# Mount domain route modules
api_router.include_router(routes_auth.router)
api_router.include_router(routes_public_campaigns.router)
api_router.include_router(routes_campaigns.router)
api_router.include_router(routes_registration.router)
api_router.include_router(routes_challenges.router)
api_router.include_router(routes_entitlements.router)
api_router.include_router(routes_metrics.router)
api_router.include_router(routes_audit.router)
api_router.include_router(routes_admin.router)

# Alias for backwards compatibility
v1_router = api_router
