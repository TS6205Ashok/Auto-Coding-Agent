from fastapi import FastAPI
import uvicorn

from app.config import settings
from app.routers import health, items


GENERATED_VERSION = "Project Agent Generated Starter v1"
app = FastAPI(title="Project Agent Starter API")
app.include_router(health.router)
app.include_router(items.router, prefix="/api/items", tags=["items"])


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Project is running",
        "version": GENERATED_VERSION,
        "environment": settings.app_env,
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
