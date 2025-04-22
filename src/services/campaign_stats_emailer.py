import logging
from datetime import datetime, timezone
from typing import List

from src.database import supabase

logger = logging.getLogger(__name__)

async def get_pending_campaign_schedules(limit: int = 100) -> List[dict]:
    """
    Fetch pending campaign message schedules that are due for processing.
    
    Args:
        limit: Maximum number of records to fetch (default: 100)
        
    Returns:
        List of campaign message schedule records
    """
    try:
        current_date = datetime.now(timezone.utc).isoformat()
        
        response = supabase.table('campaign_message_schedule')\
            .select('*')\
            .eq('status', 'pending')\
            .lte('scheduled_for', current_date)\
            .limit(limit)\
            .execute()
            
        return response.data
    except Exception as e:
        logger.error(f"Error fetching pending campaign schedules: {str(e)}")
        raise 