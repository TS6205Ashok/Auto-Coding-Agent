from pydantic import BaseModel
from fastapi import APIRouter

from app.services.chatbot_service import handle_chat_message


router = APIRouter(tags=["chatbot"])


class ChatRequest(BaseModel):
    message: str
    customer_id: str | None = None
    otp: str | None = None
    session_id: str = "default"


class ChatResponse(BaseModel):
    intent: str
    reply: str
    requires_customer_id: bool = False
    requires_otp: bool = False


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = handle_chat_message(
        message=request.message,
        customer_id=request.customer_id,
        otp=request.otp,
        session_id=request.session_id,
    )
    return ChatResponse(**result)
