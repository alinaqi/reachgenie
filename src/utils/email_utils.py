from uuid import UUID
from src.config import get_settings

def add_tracking_pixel(body: str, email_log_id: UUID) -> str:
    """
    Add a tracking pixel to an HTML email body.
    
    Args:
        body: The HTML email body content
        email_log_id: UUID of the email log for tracking
        
    Returns:
        str: The email body with tracking pixel added
    """
    settings = get_settings()
    tracking_pixel_url = f"{settings.webhook_base_url}/api/track-email/{email_log_id}"
    tracking_pixel = (
        f'<img src="{tracking_pixel_url}" '
        'width="1" height="1" '
        'style="display:none" '
        'alt="" '
        'referrerpolicy="no-referrer-when-downgrade" '
        'loading="eager" '
        '/>'
    )
    
    # Append tracking pixel to the body
    if "</body>" in body:
        return body.replace("</body>", f"{tracking_pixel}</body>")
    else:
        return f"{body}{tracking_pixel}" 