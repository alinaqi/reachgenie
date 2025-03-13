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