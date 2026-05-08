from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.services.banking_service import (
    block_card,
    get_balance,
    get_complaint_status,
    get_customer,
    get_loan_details,
    get_locations,
    get_transactions,
)


router = APIRouter(tags=["banking"])


class BlockCardRequest(BaseModel):
    customer_id: str
    otp: str
    card_last4: str = "1234"


@router.get("/customer/{customer_id}")
def read_customer(customer_id: str) -> dict:
    customer = get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/balance/{customer_id}")
def read_balance(customer_id: str) -> dict:
    return get_balance(customer_id)


@router.get("/transactions/{customer_id}")
def read_transactions(customer_id: str) -> dict:
    return {"transactions": get_transactions(customer_id)}


@router.post("/block-card")
def block_customer_card(payload: BlockCardRequest) -> dict:
    return block_card(payload.customer_id, payload.otp, payload.card_last4)


@router.get("/loan/{customer_id}")
def read_loan(customer_id: str) -> dict:
    return get_loan_details(customer_id)


@router.get("/complaint/{complaint_id}")
def read_complaint(complaint_id: str) -> dict:
    return get_complaint_status(complaint_id)


@router.get("/locations")
def read_locations() -> dict:
    return {"locations": get_locations()}
