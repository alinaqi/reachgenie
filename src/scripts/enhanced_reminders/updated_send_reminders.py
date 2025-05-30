# Updated send_reminders.py with Enhanced Reminder System Integration
# This shows the key modifications needed to integrate the enhanced reminder system

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
from src.utils.encryption import decrypt_password

# Import the enhanced reminder generator
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from enhanced_reminders.enhanced_reminder_generator import get_enhanced_reminder_content

logger = logging.getLogger(__name__)
settings = get_settings()

async def get_email_metrics_for_log(email_log_id: UUID) -> Dict:
    """Get email engagement metrics for a specific email log"""
    try:
        # Check if tables exist, otherwise use defaults
        metrics = {
            'opens': 0,
            'clicks': 0,
            'time_spent_seconds': 0,
            'open_times': [],
            'clicked_links': []
        }
        
        # Try to get actual metrics if tables exist
        try:
            # Get opens
            opens_response = supabase.table('email_opens')\
                .select('*')\
                .eq('email_log_id', str(email_log_id))\
                .execute()
            
            if opens_response.data:
                metrics['opens'] = len(opens_response.data)