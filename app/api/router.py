"""Aggregates API version routers."""

from fastapi import APIRouter

from app.api.v1.router import api_router_v1
from app.core.config import settings

api_router = APIRouter(prefix=settings.api_prefix)

api_router.include_router(api_router_v1)
