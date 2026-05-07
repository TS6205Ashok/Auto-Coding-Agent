from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_inventory() -> dict[str, str]:
    return {
        "message": "Inventory workflow and APIs.",
        "project": "Powered Inventory Decision Support",
    }
