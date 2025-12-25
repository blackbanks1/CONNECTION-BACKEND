# connection-backend/utils.py
def normalizeRwandaNumber(phone: str) -> str:
    """Normalize Rwandan phone numbers to +250 format."""
    phone = phone.strip()
    if phone.startswith("0"):
        return "+250" + phone[1:]
    if phone.startswith("+250"):
        return phone
    return None