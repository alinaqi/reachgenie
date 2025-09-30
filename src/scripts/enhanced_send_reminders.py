import logging
import asyncio
from typing import Dict
from uuid import UUID
from datetime import datetime, timezone
from src.config import get_settings
from src.database import (
    get_email_logs_reminder, 
    get_first_email_detail,
    update_reminder_sent_status,
    get_campaigns,
    get_company_by_id,
    add_email_to_queue,
    get_email_log_by_id,
    get_campaign_by_id,
    supabase
)
# Import the enhanced reminder generator
from .enhanced_reminders.enhanced_reminder_generator import get_enhanced_reminder_content

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure OpenAI
settings = get_settings()

async def get_email_metrics_for_log(email_log_id: UUID) -> Dict:
    """Get email engagement metrics for a specific email log"""
    try:
        # Query for email opens
        opens_response = supabase.table('email_opens')\
            .select('*')\
            .eq('email_log_id', str(email_log_id))\
            .execute()
        
        # Query for email clicks
        clicks_response = supabase.table('email_clicks')\
            .select('*')\
            .eq('email_log_id', str(email_log_id))\
            .execute()
        
        opens = len(opens_response.data) if opens_response.data else 0
        clicks = len(clicks_response.data) if clicks_response.data else 0
        
        # Get open times for behavioral analysis
        open_times = []
        if opens_response.data:
            open_times = [open['created_at'] for open in opens_response.data]