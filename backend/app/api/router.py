from fastapi import APIRouter
from .projects import router as projects_router
from .pages import router as pages_router
from .regions import router as regions_router
from .detection import router as detection_router
from .exports import router as exports_router
from .jobs import router as jobs_router
from .vector import router as vector_router

api_router = APIRouter()
api_router.include_router(projects_router, tags=["projects"])
api_router.include_router(pages_router, tags=["pages"])
api_router.include_router(regions_router, tags=["regions"])
api_router.include_router(detection_router, tags=["detection"])
api_router.include_router(exports_router, tags=["exports"])
api_router.include_router(jobs_router, tags=["jobs"])
api_router.include_router(vector_router, tags=["vector"])
