import json
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "dummy_customers.json"


def _load_data() -> dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_customer(customer_id: str) -> dict[str, Any] | None:
    return _load_data()["customers"].get(customer_id)


def _require_customer(customer_id: str) -> dict[str, Any]:
    customer = get_customer(customer_id)
    if not customer:
        raise ValueError(f"Customer {customer_id} was not found.")
    return customer


def verify_otp(customer_id: str, otp: str | None) -> bool:
    customer = _require_customer(customer_id)
    return str(customer.get("otp")) == str(otp or "")


def get_balance(customer_id: str) -> dict[str, Any]:
    customer = _require_customer(customer_id)
    return {"customer_id": customer_id, "available_balance": customer["account_balance"]}


def get_transactions(customer_id: str) -> list[dict[str, Any]]:
    return list(_require_customer(customer_id).get("recent_transactions", []))


def block_card(customer_id: str, otp: str | None, card_last4: str = "1234") -> dict[str, Any]:
    if not verify_otp(customer_id, otp):
        return {"status": "otp_required", "message": "OTP verification failed or is required."}
    customer = _require_customer(customer_id)
    for card in customer.get("cards", []):
        if card.get("last4") == card_last4:
            card["status"] = "blocked"
            return {"status": "blocked", "message": f"Card ending with {card_last4} has been blocked."}
    return {"status": "not_found", "message": "Card was not found."}


def get_loan_details(customer_id: str) -> dict[str, Any]:
    return dict(_require_customer(customer_id).get("loan", {}))


def get_complaint_status(complaint_id: str) -> dict[str, Any]:
    for customer in _load_data()["customers"].values():
        for complaint in customer.get("complaints", []):
            if complaint.get("complaint_id") == complaint_id:
                return complaint
    return {"complaint_id": complaint_id, "status": "not_found"}


def get_locations() -> list[dict[str, Any]]:
    return list(_load_data().get("locations", []))
