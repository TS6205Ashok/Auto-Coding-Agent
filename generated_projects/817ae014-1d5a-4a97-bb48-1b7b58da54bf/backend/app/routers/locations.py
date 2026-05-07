from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_locations() -> dict[str, str]:
    return {
        "message": "Branch and ATM location workflow and APIs.",
        "project": "Customer Chatbot Ivr For",
    }
