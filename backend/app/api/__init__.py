"""API Routers Package."""
from fastapi import APIRouter
from .routes_jobs import router as jobs_router
from .routes_repo import router as repo_router

api_router = APIRouter(prefix="/api")
api_router.include_router(repo_router)
api_router.include_router(jobs_router)

__all__ = ["api_router", "jobs_router", "repo_router"]
