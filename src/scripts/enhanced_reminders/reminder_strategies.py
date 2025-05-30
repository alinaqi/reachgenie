from typing import Dict, Optional
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

def get_progressive_reminder_strategy(reminder_type: Optional[str], lead_info: Dict, email_metrics: Dict) -> Dict:
    """
    Get progressive reminder strategy based on reminder sequence and engagement data
    
    Returns strategy with tone, approach, focus areas, and dynamic elements
    """
    
    # Calculate engagement level
    engagement_level = calculate_engagement_level(email_metrics)
    
    # Base strategies for each reminder stage
    strategies = {
        None: {  # First reminder
            "name": "Gentle Follow-up",
            "tone": "friendly and understanding",
            "approach": "acknowledge they might be busy, briefly reiterate main value proposition",
            "focus": "convenience and timing",
            "cta": "simple yes/no question or request for best time to connect",
            "urgency_level": "low",
            "personalization_depth": "medium"
        },
        "r1": {  # Second reminder
            "name": "Value Addition",
            "tone": "helpful and consultative",
            "approach": "share new insight, resource, or case study relevant to their industry",
            "focus": "educational value and expertise demonstration",
            "cta": "offer specific value exchange (free assessment, benchmark report, etc.)",
            "urgency_level": "low-medium",
            "personalization_depth": "high"
        },
        "r2": {  # Third reminder
            "name": "Social Proof",
            "tone": "confident and success-oriented",
            "approach": "share specific success story from similar company/role",
            "focus": "results and ROI demonstration",
            "cta": "propose specific meeting time with clear agenda",
            "urgency_level": "medium",
            "personalization_depth": "high"
        },
        "r3": {  # Fourth reminder
            "name": "Problem-Solution Fit",
            "tone": "direct and problem-solving focused",
            "approach": "address specific pain point based on their industry/role challenges"
        }
    }