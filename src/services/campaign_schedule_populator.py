import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from src.database import supabase

logger = logging.getLogger(__name__)

async def get_running_campaign_runs(offset: int = 0, limit: int = 100) -> List[dict]:
    """
    Fetch running campaign runs in a paginated manner.
    
    Args:
        offset: Offset for pagination
        limit: Limit for pagination
        
    Returns:
        List of running campaign runs
    """
    response = supabase.table('campaign_runs')\
        .select('*')\
        .eq('status', 'running')\
        .range(offset, offset + limit - 1)\
        .execute()
    
    return response.data

async def create_campaign_schedule(
    campaign_run_id: UUID,
    scheduled_for: datetime,
    data_fetch_date: datetime
) -> Optional[dict]:
    """
    Create a new campaign message schedule entry if it doesn't exist.
    
    Args:
        campaign_run_id: ID of the campaign run
        scheduled_for: When the message should be scheduled for
        data_fetch_date: When the data should be fetched
        
    Returns:
        Created schedule entry or None if already exists
    """
    try:
        response = supabase.table('campaign_message_schedule')\
            .insert({
                'campaign_run_id': str(campaign_run_id),
                'status': 'pending',
                'scheduled_for': scheduled_for.isoformat(),
                'data_fetch_date': data_fetch_date.isoformat()
            })\
            .execute()
            
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating schedule for campaign run {campaign_run_id}: {str(e)}")
        return None

async def populate_campaign_schedules() -> None:
    """
    Main function to populate campaign schedules for running campaigns.
    """
    offset = 0
    limit = 100
    current_date = datetime.now(timezone.utc).date()
    data_fetch_date = current_date - timedelta(days=1)
    
    while True:
        campaign_runs = await get_running_campaign_runs(offset, limit)
        if not campaign_runs:
            break
            
        for run in campaign_runs:
            schedule = await create_campaign_schedule(
                run['id'],
                datetime.combine(current_date, datetime.min.time()),
                datetime.combine(data_fetch_date, datetime.min.time())
            )
            if schedule:
                logger.info(f"Created schedule for campaign run {run['id']}")
            
        offset += limit 