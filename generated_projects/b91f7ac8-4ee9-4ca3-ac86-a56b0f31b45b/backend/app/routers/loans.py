from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_loans() -> dict[str, str]:
    return {
        "message": "Loan and EMI workflow and APIs.",
        "project": "Customer Chatbot Ivr For",
    }
