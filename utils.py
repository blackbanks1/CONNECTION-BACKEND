# connection-backend/utils.py
import re

def normalizeRwandaNumber(phone: str):
    """
    Normalize Rwandan phone numbers to standard 2507XXXXXXXX format.
    
    Supports:
    - 0788123456 → 250788123456
    - +250788123456 → 250788123456  
    - 250788123456 → 250788123456
    - 788123456 → 250788123456
    
    Returns normalized 12-digit string or None if invalid.
    """
    if not phone or not isinstance(phone, str):
        return None
    
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    
    # Validate length and pattern
    if len(digits) == 12 and digits.startswith('250'):
        # Already in 250XXXXXXXXX format
        return digits
    
    elif len(digits) == 10 and digits.startswith('07'):
        # 07XXXXXXXX format
        return '250' + digits[1:]  # Remove leading 0, add 250
    
    elif len(digits) == 9 and digits.startswith('7'):
        # 7XXXXXXXX format (no country code)
        return '250' + digits
    
    elif len(digits) == 12 and digits.startswith('+'):
        # +250XXXXXXXX format
        return digits[1:] if digits.startswith('+250') else None
    
    else:
        # Invalid format
        return None


def formatRwandaNumberForDisplay(phone: str) -> str:
    """
    Format normalized phone for display: 250788123456 → 0788 123 456
    """
    normalized = normalizeRwandaNumber(phone)
    if not normalized or len(normalized) != 12:
        return phone
    
    # 250788123456 → 0788 123 456
    local_part = normalized[3:]  # Remove 250
    formatted = f"0{local_part[:3]} {local_part[3:6]} {local_part[6:]}"
    return formatted


def validateRwandaPhone(phone: str) -> bool:
    """
    Check if a phone number is a valid Rwanda number.
    """
    normalized = normalizeRwandaNumber(phone)
    return normalized is not None and len(normalized) == 12


# Optional: For database queries
def normalize_for_query(phone: str):
    """
    Alias for normalizeRwandaNumber for clarity in database operations.
    """
    return normalizeRwandaNumber(phone)


# Optional: For user input cleaning
def clean_phone_input(phone: str) -> str:
    """
    Clean phone input by removing spaces, dashes, etc.
    Returns the raw digits.
    """
    if not phone:
        return ""
    return re.sub(r'\D', '', phone)