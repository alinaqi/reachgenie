import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
from openai import AsyncOpenAI
from src.config import get_settings
from src.database import get_lead_by_id, get_product_by_id
import json

logger = logging.getLogger(__name__)
settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

# Progressive reminder strategies for 7 reminders
REMINDER_STRATEGIES = {
    None: {  # First reminder
        "name": "Gentle Follow-up",
        "tone": "friendly and understanding",
        "approach": "acknowledge they might be busy, briefly reiterate main value proposition",
        "focus": "convenience and timing",
        "cta": "simple yes/no question or request for best time to connect",
        "urgency_level": "low"
    },
    "r1": {  # Second reminder
        "name": "Value Addition",
        "tone": "helpful and consultative",
        "approach": "share new insight, resource, or case study relevant to their industry",
        "focus": "educational value and expertise demonstration",
        "cta": "offer specific value exchange (free assessment, benchmark report, etc.)",
        "urgency_level": "low-medium"
    },
    "r2": {  # Third reminder
        "name": "Social Proof",
        "tone": "confident and success-oriented",
        "approach": "share specific success story from similar company/role",
        "focus": "results and ROI demonstration",
        "cta": "propose specific meeting time with clear agenda",
        "urgency_level": "medium"
    },
    "r3": {  # Fourth reminder
        "name": "Problem-Solution Fit",
        "tone": "direct and problem-solving focused",
        "approach": "address specific pain point based on their industry/role challenges",
        "focus": "specific problems we solve",
        "cta": "offer quick diagnostic call or problem-solving session",
        "urgency_level": "medium-high"
    },
    "r4": {  # Fifth reminder
        "name": "Urgency Creation",
        "tone": "professional with subtle urgency",
        "approach": "mention time-sensitive opportunity, limited availability, or market changes"        "focus": "opportunity cost and competitive advantage",
        "cta": "specific deadline or limited-time offer",
        "urgency_level": "high"
    },
    "r5": {  # Sixth reminder
        "name": "Alternative Approach",
        "tone": "casual and peer-to-peer",
        "approach": "try different angle - maybe they're not the right person, ask for referral",
        "focus": "finding the right fit",
        "cta": "ask if someone else handles this or if priorities have changed",
        "urgency_level": "low"
    },
    "r6": {  # Seventh reminder
        "name": "Professional Break-up",
        "tone": "respectful and final",
        "approach": "acknowledge lack of response, provide easy opt-out, leave door open",
        "focus": "respect for their time and inbox",
        "cta": "final value offer with easy yes/no response option",
        "urgency_level": "none"
    }
}

def calculate_engagement_level(email_metrics: Dict) -> str:
    """Calculate engagement level based on email metrics"""
    opens = email_metrics.get('opens', 0)
    clicks = email_metrics.get('clicks', 0)
    
    if clicks > 0:
        return "high"
    elif opens > 2:
        return "medium"
    elif opens > 0:
        return "low"
    else:
        return "none"

def get_dynamic_content_elements(lead_info: Dict, reminder_type: Optional[str]) -> Dict:
    """Get dynamic content elements based on lead info and timing"""
    current_time = datetime.now(timezone.utc)
    current_day = current_time.strftime("%A")
    current_month = current_time.strftime("%B")
    
    elements = {
        "time_reference": "",
        "role_reference": "",
        "industry_challenge": ""
    }
    
    # Time-based elements
    if current_day == "Monday":
        elements["time_reference"] = "start of the week"    elif current_day == "Friday":
        elements["time_reference"] = "before the weekend"
    elif current_time.day <= 7:
        elements["time_reference"] = f"beginning of {current_month}"
    elif current_time.day >= 24:
        elements["time_reference"] = f"end of {current_month}"
    
    # Role-based elements
    job_title = lead_info.get('job_title', '').lower()
    if any(exec in job_title for exec in ['ceo', 'cto', 'cfo', 'vp', 'director']):
        elements["role_reference"] = "strategic initiatives"
    elif any(mgr in job_title for mgr in ['manager', 'head of']):
        elements["role_reference"] = "team efficiency"
    
    # Industry challenges
    industry = lead_info.get('industry', '').lower()
    industry_challenges = {
        'technology': 'staying ahead of rapid innovation',
        'finance': 'navigating compliance and digital transformation',
        'healthcare': 'improving patient outcomes while managing costs',
        'retail': 'enhancing customer experience across channels',
        'manufacturing': 'optimizing supply chain efficiency'
    }
    
    for ind, challenge in industry_challenges.items():
        if ind in industry:
            elements["industry_challenge"] = challenge
            break
    
    return elements

async def get_enhanced_reminder_content(
    original_email_body: str,
    reminder_type: Optional[str],
    company_info: Dict,
    lead_id: str,
    campaign: Dict,
    email_metrics: Dict = None
) -> Tuple[str, str]:
    """Generate enhanced reminder with progressive strategies and dynamic content"""
    
    # Get lead information
    lead_info = await get_lead_by_id(lead_id)
    if not lead_info:
        logger.error(f"Lead not found: {lead_id}")
        return None, None
    
    # Get product information
    product = await get_product_by_id(campaign['product_id'])
    product_info = product.get('description', '') if product else ''    
    # Default email metrics if not provided
    if email_metrics is None:
        email_metrics = {'opens': 0, 'clicks': 0}
    
    # Get strategy and engagement level
    strategy = REMINDER_STRATEGIES.get(reminder_type, REMINDER_STRATEGIES[None])
    engagement_level = calculate_engagement_level(email_metrics)
    
    # Get dynamic content elements
    dynamic_elements = get_dynamic_content_elements(lead_info, reminder_type)
    
    # Adjust strategy based on engagement
    if engagement_level == "high":
        strategy["tone"] = "assumptive and action-oriented"
        strategy["approach"] = "reference their interest, be more direct"
    elif engagement_level == "none" and reminder_type in ["r2", "r3"]:
        strategy["approach"] = "try completely different angle"
    
    # Build behavioral modifiers
    behavioral_notes = ""
    if email_metrics.get('opens', 0) > 3:
        behavioral_notes = "Lead has opened previous emails multiple times - showing interest"
    elif email_metrics.get('clicks', 0) > 0:
        behavioral_notes = "Lead clicked links - high engagement"
    
    # Create the enhanced prompt
    system_prompt = f"""You are an expert sales professional creating a {strategy['name']} reminder email.
    
Strategy Details:
- Tone: {strategy['tone']}
- Approach: {strategy['approach']}
- Focus: {strategy['focus']}
- CTA: {strategy['cta']}
- Urgency Level: {strategy['urgency_level']}
- Engagement Level: {engagement_level}

Lead Information:
- Name: {lead_info.get('first_name', '')} {lead_info.get('last_name', '')}
- Company: {lead_info.get('company', '')}
- Role: {lead_info.get('job_title', '')}
- Industry: {lead_info.get('industry', '')}
- Company Size: {lead_info.get('company_size', '')}

Dynamic Elements to Consider:
- Time Context: {dynamic_elements.get('time_reference', '')}
- Role Context: {dynamic_elements.get('role_reference', '')}
- Industry Challenge: {dynamic_elements.get('industry_challenge', '')}

Behavioral Notes: {behavioral_notes}

Company Information (for signature):
- Company URL: {company_info.get('website', '')}
- Contact Person: {company_info.get('account_email', '').split('@')[0]}
- Calendar Link: {company_info.get('custom_calendar_link', '')}"""
    user_prompt = f"""Generate a {strategy['name']} reminder email based on the original email below.

Important Guidelines:
1. Generate ONLY the email body content
2. Apply the strategy tone and approach specified
3. Include relevant dynamic elements naturally
4. Reference the original email appropriately for this reminder stage
5. End with the specified CTA type
6. For high engagement: be more direct and assumptive
7. For no engagement: try a different angle if this is reminder 3-5
8. Make it feel personalized and human, not templated
9. Keep it concise - {strategy['name']} emails should be shorter than original
10. Include proper signature with calendar link if available

Original Email:
{original_email_body}

Product Information:
{product_info}

Remember: This is reminder #{get_reminder_number(reminder_type)} of 7 total reminders."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,  # Slightly higher for more variation
            max_tokens=400
        )
        
        reminder_body = response.choices[0].message.content.strip()
        
        # Generate subject line based on strategy
        subject = generate_reminder_subject(
            reminder_type,
            original_email_body,
            lead_info,
            engagement_level
        )
        
        return subject, reminder_body.replace('\n', '<br>')
        
    except Exception as e:
        logger.error(f"Error generating enhanced reminder: {str(e)}")
        return None, None

def get_reminder_number(reminder_type: Optional[str]) -> int:
    """Get reminder number from type"""
    if reminder_type is None:
        return 1
    return int(reminder_type[1]) + 1 if reminder_type.startswith('r') else 1
def generate_reminder_subject(
    reminder_type: Optional[str],
    original_email_body: str,
    lead_info: Dict,
    engagement_level: str
) -> str:
    """Generate dynamic subject line based on strategy and engagement"""
    
    # Extract original subject from email if possible
    import re
    subject_match = re.search(r'Subject: (.+?)(?:\n|$)', original_email_body)
    original_subject = subject_match.group(1) if subject_match else "our conversation"
    
    # Subject line templates based on reminder stage
    subject_templates = {
        None: "Re: {original}",
        "r1": "Quick question about {company}",
        "r2": "Saw this and thought of {first_name}",
        "r3": "{first_name}, solving {industry} challenges",
        "r4": "Time-sensitive for {company}",
        "r5": "Wrong person? Re: {original}",
        "r6": "Final note for {first_name}"
    }
    
    # Adjust for low engagement
    if engagement_level == "none" and reminder_type in ["r2", "r3"]:
        subject_templates[reminder_type] = "{first_name}, fresh perspective on {industry}"
    
    template = subject_templates.get(reminder_type, "Following up")
    
    # Fill in the template
    subject = template.format(
        original=original_subject,
        company=lead_info.get('company', 'your company'),
        first_name=lead_info.get('first_name', ''),
        industry=lead_info.get('industry', 'your industry')
    )
    
    return subject