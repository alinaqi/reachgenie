from typing import Dict, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def calculate_engagement_level(email_metrics: Dict) -> str:
    """Calculate engagement level based on email metrics"""
    
    opens = email_metrics.get('opens', 0)
    clicks = email_metrics.get('clicks', 0)
    time_spent = email_metrics.get('time_spent_seconds', 0)
    
    if clicks > 0:
        return "high"
    elif opens > 2 or time_spent > 30:
        return "medium"
    elif opens > 0:
        return "low"
    else:
        return "none"


def adjust_strategy_for_engagement(strategy: Dict, engagement_level: str, email_metrics: Dict) -> Dict:
    """Adjust strategy based on engagement level"""
    
    if engagement_level == "high":
        strategy["tone"] = "assumptive and action-oriented"
        strategy["approach"] = f"reference their interest (clicked links), be more direct"
        strategy["urgency_level"] = "high"
        strategy["cta"] = "immediate action - book time now"
        
    elif engagement_level == "medium":
        strategy["approach"] = f"acknowledge their consideration, {strategy['approach']}"
        strategy["urgency_level"] = "medium-high"
        
    elif engagement_level == "none" and strategy.get("name") != "Professional Break-up":
        # Try different subject line approach for no engagement
        strategy["subject_line_approach"] = "completely different angle"
        
    return strategy


def analyze_common_open_time(open_times: list) -> int:
    """Analyze common email open times to suggest best send time"""
    if not open_times:
        return 9  # Default to 9 AM
        
    # Simple analysis - get most common hour
    hours = [datetime.fromisoformat(t.replace('Z', '+00:00')).hour for t in open_times if t]
    if hours:
        return max(set(hours), key=hours.count)
    return 9