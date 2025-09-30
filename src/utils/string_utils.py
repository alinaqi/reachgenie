import re

def _extract_name_from_email(email: str) -> str:
    """
    Extract name from email address and format it as a proper name
    (e.g., 'Jack Doe' from 'jack.doe@gmail.com')
    """
    # Get the part before @
    local_part = email.split('@')[0]
    
    # Replace common separators with spaces
    name = local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    
    # Split into parts and capitalize each part
    name_parts = [part.capitalize() for part in name.split() if part]
    
    # If we have at least one part, return the formatted name
    if name_parts:
        return ' '.join(name_parts)
    
    # Fallback to just capitalize the local part if splitting produces no valid parts
    return local_part.capitalize()

def validate_phone_number(phone: str) -> tuple[bool, str]:
    """
    Validate and format phone number to E.164 format.
    Returns (is_valid, formatted_number) tuple.
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if we have a reasonable number of digits (most countries between 10-15 digits)
    if len(digits_only) < 10 or len(digits_only) > 15:
        return False, ""
    
    # If number doesn't start with +, check if it needs a country code
    if not phone.startswith('+'):
        # If it's a 10-digit number, assume US/Canada (+1)
        if len(digits_only) == 10:
            formatted = f"+1{digits_only}"
        # If it starts with 1 and has 11 digits, assume US/Canada
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            formatted = f"+{digits_only}"
        else:
            return False, ""
    else:
        formatted = f"+{digits_only}"
    
    # Validate the final format matches E.164 (+ followed by 10-15 digits)
    if re.match(r'^\+\d{10,15}$', formatted):
        return True, formatted
    
    return False, ""