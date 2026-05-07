from app.services.banking_service import (
    block_card,
    get_balance,
    get_complaint_status,
    get_loan_details,
    get_locations,
    get_transactions,
    verify_otp,
)
from app.services.intent_service import detect_intent


SECURE_INTENTS = {"balance_enquiry", "recent_transactions", "card_blocking", "loan_emi"}


def handle_chat_message(message: str, customer_id: str | None = None, otp: str | None = None, session_id: str = "default") -> dict:
    intent = detect_intent(message)
    if intent in SECURE_INTENTS and not customer_id:
        return {
            "intent": intent,
            "reply": "Please enter your customer ID.",
            "requires_customer_id": True,
            "requires_otp": False,
        }
    if intent in SECURE_INTENTS and not verify_otp(customer_id or "", otp):
        return {
            "intent": intent,
            "reply": "Please verify OTP. For demo customer CUST1001, use OTP 123456.",
            "requires_customer_id": False,
            "requires_otp": True,
        }
    if intent == "balance_enquiry":
        balance = get_balance(customer_id or "")
        return {"intent": intent, "reply": f"Your available balance is Rs. {balance['available_balance']:,.2f}."}
    if intent == "recent_transactions":
        transactions = get_transactions(customer_id or "")
        lines = [f"{item['date']} - {item['description']} - Rs. {item['amount']}" for item in transactions]
        return {"intent": intent, "reply": "Recent transactions: " + "; ".join(lines)}
    if intent == "card_blocking":
        result = block_card(customer_id or "", otp, "1234")
        return {"intent": intent, "reply": result["message"]}
    if intent == "loan_emi":
        loan = get_loan_details(customer_id or "")
        return {"intent": intent, "reply": f"Your loan EMI is Rs. {loan.get('emi')} due on {loan.get('next_due_date')}."}
    if intent == "complaint_status":
        return {"intent": intent, "reply": f"Complaint status: {get_complaint_status('CMP9001').get('status')}."}
    if intent == "branch_atm_search":
        locations = get_locations()
        names = ", ".join(item["name"] for item in locations)
        return {"intent": intent, "reply": f"Nearest branch/ATM options: {names}."}
    if intent == "human_agent_transfer":
        return {"intent": intent, "reply": "I am transferring you to a human support agent queue."}
    return {"intent": intent, "reply": "I can help with balance, transactions, card blocking, loan EMI, complaints, branches, ATMs, and FAQs."}
