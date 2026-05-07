from fastapi import FastAPI
import uvicorn

from app.config import settings
from app.routers import banking, chatbot, health, items


GENERATED_VERSION = "Project Agent Generated Starter v1"
app = FastAPI(title="The Proposed System Is API")
app.include_router(health.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")
app.include_router(banking.router, prefix="/api/banking")
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
