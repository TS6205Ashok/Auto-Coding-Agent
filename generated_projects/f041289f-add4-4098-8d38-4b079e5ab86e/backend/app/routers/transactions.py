from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_transactions() -> dict[str, str]:
    return {
        "message": "Transaction lookup workflow and APIs.",
        "project": "The Proposed System Is",
    }
