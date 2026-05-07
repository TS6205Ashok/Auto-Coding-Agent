from fastapi import APIRouter

from app.schemas.health import HealthResponse

GENERATED_VERSION = "Project Agent Generated Starter v1"
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", message="Project is running", version=GENERATED_VERSION)
