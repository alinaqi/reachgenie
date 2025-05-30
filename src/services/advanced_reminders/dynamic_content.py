"""
Dynamic Content Generation for Personalized Reminders
Handles time-based, industry-specific, and contextual content
"""

from datetime import datetime, timezone
import random
from typing import Dict, List, Optional

# Industry-specific pain points and benefits
INDUSTRY_PAIN_POINTS = {
    "saas": ["churn reduction", "user onboarding", "feature adoption", "scaling challenges"],
    "ecommerce": ["cart abandonment", "inventory management", "customer retention", "shipping costs"],
    "finance": ["compliance burden", "risk assessment", "customer verification", "fraud detection"],
    "healthcare": ["patient engagement", "appointment no-shows", "data security", "billing complexity"],
    "manufacturing": ["supply chain visibility", "quality control", "downtime costs", "inventory optimization"],
    "retail": ["omnichannel experience", "inventory turnover", "customer loyalty", "seasonal fluctuations"],
    "technology": ["talent retention", "development velocity", "technical debt", "deployment efficiency"],
    "education": ["student engagement", "retention rates", "administrative burden", "budget constraints"],
    "real estate": ["lead conversion", "property management", "market analysis", "client communication"],
    "marketing": ["attribution tracking", "ROI measurement", "lead quality", "campaign optimization"]
}

# Time-based greetings and context
def get_time_based_greeting(timezone_str: str = "UTC") -> str:
    """Generate greeting based on recipient's local time"""
    now = datetime.now(timezone.utc)
    hour = now.hour
    
    if 5 <= hour < 12:
        greetings = [
            "Good morning",
            "Hope you're having a great morning",
            "Morning",
            "Hope your day is off to a good start"
        ]
    elif 12 <= hour < 17:
        greetings = [
            "Good afternoon", 
            "Hope you're having a productive afternoon",
            "Afternoon",
            "Hope your day is going well"
        ]
    elif 17 <= hour < 21:
        greetings = [
            "Good evening",
            "Hope you're wrapping up a successful day",
            "Evening",
            "Hope you had a great day"
        ]
    else:
        greetings = [
            "Hi",
            "Hello",
            "Hope this finds you well",
            "Greetings"
        ]
    
    return random.choice(greetings)

def get_day_context() -> Dict[str, any]:
    """Get context based on day of week and time of year"""
    now = datetime.now()
    day_of_week = now.strftime("%A")
    month = now.strftime("%B")
    
    context = {
        "day_of_week": day_of_week,
        "month": month,
        "is_monday": now.weekday() == 0,
        "is_friday": now.weekday() == 4,
        "is_month_end": now.day >= 25,
        "is_quarter_end": now.month in [3, 6, 9, 12] and now.day >= 20,
        "is_year_end": now.month == 12
    }
    
    # Special period contexts
    if context["is_monday"]:
        context["day_context"] = "start of the week"
    elif context["is_friday"]:
        context["day_context"] = "end of the week"
    elif context["is_month_end"]:
        context["day_context"] = "end of the month"
    elif context["is_quarter_end"]:
        context["day_context"] = "end of the quarter"
    else:
        context["day_context"] = "week"
        
    return context

def get_seasonal_context() -> Dict[str, str]:
    """Get seasonal business context"""
    month = datetime.now().month
    
    seasonal_contexts = {
        1: {"season": "new year", "business_focus": "annual planning", "mood": "fresh start"},
        2: {"season": "early year", "business_focus": "execution", "mood": "momentum building"},
        3: {"season": "Q1 end", "business_focus": "quarterly reviews", "mood": "assessment"},
        4: {"season": "spring", "business_focus": "growth initiatives", "mood": "renewal"},
        5: {"season": "mid-year approach", "business_focus": "acceleration", "mood": "urgency"},
        6: {"season": "mid-year", "business_focus": "half-year review", "mood": "evaluation"},
        7: {"season": "summer", "business_focus": "efficiency", "mood": "optimization"},
        8: {"season": "late summer", "business_focus": "preparation", "mood": "planning ahead"},
        9: {"season": "Q3 end", "business_focus": "final push", "mood": "achievement"},
        10: {"season": "Q4 start", "business_focus": "year-end planning", "mood": "strategic"},
        11: {"season": "late year", "business_focus": "budget season", "mood": "decision time"},
        12: {"season": "year-end", "business_focus": "closing strong", "mood": "reflection"}
    }
    
    return seasonal_contexts.get(month, {"season": "current", "business_focus": "growth", "mood": "progressive"})

def get_industry_insights(industry: str, company_size: str) -> Dict[str, any]:
    """Generate industry-specific insights and talking points"""
    
    size_modifiers = {
        "1-10": "growing teams",
        "11-50": "scaling companies", 
        "51-200": "mid-market organizations",
        "201-500": "established companies",
        "501-1000": "enterprise teams",
        "1000+": "large enterprises"
    }
    
    size_context = size_modifiers.get(company_size, "organizations")
    
    insights = {
        "pain_points": INDUSTRY_PAIN_POINTS.get(industry.lower(), ["efficiency", "growth", "optimization"]),
        "size_context": size_context,
        "trending_topics": get_industry_trends(industry),
        "common_challenges": get_size_based_challenges(company_size)
    }
    
    return insights

def get_industry_trends(industry: str) -> List[str]:
    """Get current trends for specific industry"""
    trends = {
        "saas": ["PLG adoption", "AI integration", "vertical SaaS", "usage-based pricing"],
        "ecommerce": ["social commerce", "sustainability", "same-day delivery", "AR shopping"],
        "finance": ["embedded finance", "open banking", "crypto integration", "RegTech"],
        "healthcare": ["telemedicine", "AI diagnostics", "patient portals", "value-based care"],
        "manufacturing": ["Industry 4.0", "IoT sensors", "predictive maintenance", "reshoring"],
        "default": ["digital transformation", "automation", "data-driven decisions", "customer experience"]
    }
    
    return trends.get(industry.lower(), trends["default"])

def get_size_based_challenges(company_size: str) -> List[str]:
    """Get challenges based on company size"""
    challenges = {
        "1-10": ["resource constraints", "wearing multiple hats", "rapid growth", "process creation"],
        "11-50": ["scaling operations", "team coordination", "process standardization", "culture maintenance"],
        "51-200": ["departmental silos", "communication gaps", "system integration", "middle management"],
        "201-500": ["enterprise transformation", "change management", "legacy systems", "innovation speed"],
        "501-1000": ["organizational agility", "digital adoption", "cost optimization", "global coordination"],
        "1000+": ["market disruption", "innovation at scale", "regulatory compliance", "cultural transformation"]
    }
    
    return challenges.get(company_size, ["growth", "efficiency", "competitiveness"])

def personalize_message_element(template: str, lead_data: Dict, company_data: Dict) -> str:
    """Replace template variables with personalized content"""
    
    day_context = get_day_context()
    seasonal_context = get_seasonal_context()
    industry_insights = get_industry_insights(
        lead_data.get('industries', ['general'])[0] if lead_data.get('industries') else 'general',
        lead_data.get('company_size', 'unknown')
    )
    
    replacements = {
        "{first_name}": lead_data.get('first_name', lead_data.get('name', '').split()[0]),
        "{company}": lead_data.get('company', ''),
        "{job_title}": lead_data.get('job_title', ''),
        "{department}": lead_data.get('department', ''),
        "{day_of_week}": day_context['day_of_week'],
        "{day_context}": day_context['day_context'],
        "{season}": seasonal_context['season'],
        "{business_focus}": seasonal_context['business_focus'],
        "{industry}": lead_data.get('industries', ['your industry'])[0] if lead_data.get('industries') else 'your industry',
        "{pain_point}": random.choice(industry_insights['pain_points']),
        "{size_context}": industry_insights['size_context'],
        "{trending_topic}": random.choice(industry_insights['trending_topics']),
        "{challenge}": random.choice(industry_insights['common_challenges'])
    }
    
    for key, value in replacements.items():
        template = template.replace(key, str(value))
        
    return template

def generate_dynamic_ps_line(lead_data: Dict, reminder_number: int) -> Optional[str]:
    """Generate a dynamic PS line based on context"""
    
    ps_templates = {
        0: [  # First reminder
            "PS - Noticed you're in {industry}. Happy to share what's working for similar companies.",
            "PS - {first_name}, would a different time zone work better for you?",
            "PS - If email isn't ideal, I'm also on LinkedIn."
        ],
        1: [  # Second reminder  
            "PS - Attached a quick resource about {pain_point} that might help regardless.",
            "PS - Our {industry} clients typically see results within 30 days.",
            "PS - Would your {department} team benefit from this?"
        ],
        2: [  # Third reminder
            "PS - 3 {size_context} in {industry} started with us this month.",
            "PS - The {business_focus} period is when we see the most adoption.",
            "PS - Quick question: Is {challenge} a priority this quarter?"
        ]
    }
    
    templates = ps_templates.get(reminder_number, ps_templates[0])
    selected_template = random.choice(templates)
    
    return personalize_message_element(selected_template, lead_data, {})