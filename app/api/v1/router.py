"""Aggregates all v1 module routers."""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router

api_router_v1 = APIRouter()

api_router_v1.include_router(auth_router)
