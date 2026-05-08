def detect_intent(message: str) -> str:
    text = message.lower()
    if any(term in text for term in ["balance", "available amount", "account amount"]):
        return "balance_enquiry"
    if any(term in text for term in ["transaction", "statement", "recent spend"]):
        return "recent_transactions"
    if any(term in text for term in ["lost card", "block card", "debit card", "credit card"]):
        return "card_blocking"
    if any(term in text for term in ["loan", "emi"]):
        return "loan_emi"
    if any(term in text for term in ["complaint", "ticket", "case status"]):
        return "complaint_status"
    if any(term in text for term in ["branch", "atm", "location", "near me"]):
        return "branch_atm_search"
    if any(term in text for term in ["human", "agent", "representative"]):
        return "human_agent_transfer"
    return "faq"
