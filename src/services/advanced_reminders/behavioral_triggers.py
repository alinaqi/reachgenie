"""
Behavioral Triggers for Smart Reminder Personalization
Analyzes email engagement and adjusts messaging accordingly
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BehavioralAnalyzer:
    """Analyzes lead behavior and recommends reminder adjustments"""
    
    def __init__(self, email_log: Dict, lead_data: Dict):
        self.email_log = email_log
        self.lead_data = lead_data
        self.has_opened = email_log.get('has_opened', False)
        self.has_replied = email_log.get('has_replied', False)
        self.has_meeting_booked = email_log.get('has_meeting_booked', False)
        self.days_since_sent = self._calculate_days_since_sent()
        
    def _calculate_days_since_sent(self) -> int:
        """Calculate days since original email was sent"""
        sent_at = self.email_log.get('sent_at')
        if sent_at:
            if isinstance(sent_at, str):
                sent_at = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
            return (datetime.now() - sent_at).days
        return 0
    
    def get_engagement_level(self) -> str:
        """Determine engagement level based on behavior"""
        if self.has_meeting_booked:
            return "booked"
        elif self.has_replied:
            return "high"
        elif self.has_opened:
            return "medium"
        else:
            return "low"
    
    def get_behavioral_insights(self) -> Dict[str, any]:
        """Generate insights based on behavior patterns"""
        engagement_level = self.get_engagement_level()
        
        insights = {
            "engagement_level": engagement_level,
            "days_since_sent": self.days_since_sent,
            "recommended_approach": self._get_recommended_approach(engagement_level),
            "urgency_level": self._calculate_urgency(),
            "personalization_depth": self._get_personalization_depth(engagement_level),
            "tone_adjustment": self._get_tone_adjustment(engagement_level)
        }
        
        return insights
    
    def _get_recommended_approach(self, engagement_level: str) -> Dict[str, str]:
        """Recommend approach based on engagement"""
        approaches = {
            "high": {
                "strategy": "build_on_interest",
                "focus": "specific_value_props",
                "cta_type": "direct_scheduling",
                "urgency": "moderate_to_high"
            },
            "medium": {
                "strategy": "reignite_interest",
                "focus": "address_hesitations",
                "cta_type": "low_commitment_option",
                "urgency": "moderate"
            },
            "low": {
                "strategy": "new_angle",
                "focus": "different_value_prop",
                "cta_type": "educational_content",
                "urgency": "low"
            },
            "booked": {
                "strategy": "maintain_excitement",
                "focus": "prepare_for_meeting",
                "cta_type": "confirm_attendance",
                "urgency": "none"
            }
        }
        
        return approaches.get(engagement_level, approaches["low"])
    
    def _calculate_urgency(self) -> str:
        """Calculate urgency based on time and engagement"""
        if self.has_opened and self.days_since_sent < 7:
            return "high"
        elif self.has_opened and self.days_since_sent < 14:
            return "moderate"
        elif self.days_since_sent > 30:
            return "final_attempt"
        else:
            return "low"
    
    def _get_personalization_depth(self, engagement_level: str) -> str:
        """Determine how deep personalization should go"""
        if engagement_level == "high":
            return "deep"  # Use all available data
        elif engagement_level == "medium":
            return "moderate"  # Company and role specific
        else:
            return "light"  # General industry trends
    
    def _get_tone_adjustment(self, engagement_level: str) -> str:
        """Adjust tone based on engagement"""
        if engagement_level == "high":
            return "enthusiastic_professional"
        elif engagement_level == "medium":
            return "curious_helpful"
        else:
            return "respectful_patient"

def get_behavioral_reminder_adjustments(
    email_log: Dict,
    lead_data: Dict,
    reminder_type: str,
    base_strategy: Dict
) -> Dict[str, any]:
    """
    Adjust reminder strategy based on behavioral analysis
    
    Returns modified strategy with behavioral adjustments
    """
    analyzer = BehavioralAnalyzer(email_log, lead_data)
    insights = analyzer.get_behavioral_insights()
    
    # Create adjusted strategy
    adjusted_strategy = base_strategy.copy()
    
    # Adjust based on engagement level
    engagement_adjustments = {
        "high": {
            "tone_modifier": "more direct and assumptive",
            "opening_modifier": "acknowledge their interest",
            "cta_modifier": "stronger and more specific",
            "follow_up_speed": "faster"
        },
        "medium": {
            "tone_modifier": "more intriguing and value-focused",
            "opening_modifier": "reference their engagement",
            "cta_modifier": "lower commitment threshold",
            "follow_up_speed": "moderate"
        },
        "low": {
            "tone_modifier": "completely different angle",
            "opening_modifier": "fresh start approach",
            "cta_modifier": "minimal ask",
            "follow_up_speed": "slower"
        }
    }
    
    engagement_level = insights['engagement_level']
    adjustments = engagement_adjustments.get(engagement_level, engagement_adjustments["low"])
    
    # Apply adjustments
    adjusted_strategy['behavioral_insights'] = insights
    adjusted_strategy['tone'] = f"{base_strategy['tone']} - {adjustments['tone_modifier']}"
    adjusted_strategy['behavioral_adjustments'] = adjustments
    
    # Special handling for opened but not replied
    if analyzer.has_opened and not analyzer.has_replied:
        adjusted_strategy['special_handling'] = "opened_no_reply"
        adjusted_strategy['opening_lines'] = [
            "I noticed you checked out my previous email",
            "Saw you had a chance to review our conversation",
            "Thanks for taking a look at my last note",
            "Appreciate you opening my previous email"
        ]
    
    return adjusted_strategy

def get_smart_timing_recommendation(
    lead_data: Dict,
    email_log: Dict,
    company_timezone: str = "UTC"
) -> Dict[str, any]:
    """
    Recommend optimal timing for reminder based on behavior and data
    """
    recommendations = {
        "best_day": _get_best_day(lead_data),
        "best_time": _get_best_time(lead_data, email_log),
        "avoid_days": _get_days_to_avoid(lead_data),
        "urgency_factor": _calculate_timing_urgency(email_log)
    }
    
    return recommendations

def _get_best_day(lead_data: Dict) -> str:
    """Determine best day to send based on role and industry"""
    role = lead_data.get('job_title', '').lower()
    
    # C-level executives - early week
    if any(title in role for title in ['ceo', 'cto', 'cfo', 'chief', 'president']):
        return "Tuesday"
    # Sales roles - mid-week
    elif any(title in role for title in ['sales', 'business development']):
        return "Wednesday"
    # Technical roles - avoid Monday/Friday
    elif any(title in role for title in ['engineer', 'developer', 'technical']):
        return "Thursday"
    else:
        return "Tuesday"  # Default best day

def _get_best_time(lead_data: Dict, email_log: Dict) -> str:
    """Determine best time to send"""
    # If they opened previous email, try similar time
    if email_log.get('has_opened'):
        return "similar_to_last_open"
    
    role = lead_data.get('job_title', '').lower()
    
    # Early birds - executives
    if any(title in role for title in ['ceo', 'chief', 'president', 'founder']):
        return "early_morning"  # 7-9 AM
    # Standard business hours
    else:
        return "mid_morning"  # 10-11 AM

def _get_days_to_avoid(lead_data: Dict) -> list:
    """Determine days to avoid based on patterns"""
    avoid = ["Sunday", "Saturday"]  # Always avoid weekends
    
    # Some industries avoid Mondays
    industry = lead_data.get('industry', '').lower()
    if industry in ['retail', 'hospitality', 'healthcare']:
        avoid.append("Monday")
    
    return avoid

def _calculate_timing_urgency(email_log: Dict) -> str:
    """Calculate urgency for timing"""
    if email_log.get('has_opened') and not email_log.get('has_replied'):
        return "high"  # They're interested but haven't acted
    elif email_log.get('days_since_sent', 0) > 20:
        return "low"  # Been too long, no rush
    else:
        return "moderate"