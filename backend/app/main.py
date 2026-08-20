from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.router import api_router
from .config import settings


# Add /health to the API router before mounting
@api_router.get("/health")
def api_health_check():
    """API v2 health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}


app = FastAPI(
    title="Illustration Extractor API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v2")


@app.get("/health")
def root_health_check():
    """Root health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}
