from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_auth() -> dict[str, str]:
    return {
        "message": "Authentication workflow and APIs.",
        "project": "The Proposed System Is",
    }
