from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_api() -> dict[str, str]:
    return {
        "message": "API route requested from chat",
        "project": "The Proposed System Is",
    }
