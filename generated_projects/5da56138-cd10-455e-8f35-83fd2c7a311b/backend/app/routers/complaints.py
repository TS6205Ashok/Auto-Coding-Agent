from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_complaints() -> dict[str, str]:
    return {
        "message": "Complaint tracking workflow and APIs.",
        "project": "Customer Chatbot Ivr For",
    }
