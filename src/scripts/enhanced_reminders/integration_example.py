# Key Changes to integrate Enhanced Reminders into existing send_reminders.py

# 1. Replace the existing get_reminder_content function with this enhanced version:

async def get_reminder_content(original_email_body: str, reminder_type: str, company_info: Dict, log: Dict) -> str:
    """
    Generate enhanced reminder email content with progressive strategies
    """
    from enhanced_reminders.enhanced_reminder_generator import (
        REMINDER_STRATEGIES,
        calculate_engagement_level,
        get_dynamic_content_elements,
        generate_reminder_subject
    )
    
    # Get lead information from the log
    lead_id = log['lead_id']
    lead_info = await get_lead_by_id(UUID(lead_id))
    
    # Get email metrics (you can expand this based on your tracking)
    email_metrics = {
        'opens': log.get('has_opened', False) and 2 or 0,  # Simple example
        'clicks': 0  # Add click tracking if available
    }
    
    # Get strategy
    strategy = REMINDER_STRATEGIES.get(reminder_type, REMINDER_STRATEGIES[None])
    engagement_level = calculate_engagement_level(email_metrics)
    
    # Get dynamic elements
    dynamic_elements = get_dynamic_content_elements(lead_info, reminder_type)
    
    # Adjust strategy based on engagement
    if engagement_level == "high":
        strategy["tone"] = "assumptive and action-oriented"
    elif engagement_level == "none" and reminder_type in ["r2", "r3"]:
        strategy["approach"] = "try completely different angle"
    
    # Build the enhanced prompt
    system_prompt = f"""You are an expert sales professional creating a {strategy['name']} reminder.

Strategy: {strategy['tone']} tone, {strategy['approach']}
Focus: {strategy['focus']}
CTA: {strategy['cta']}

Lead: {lead_info.get('first_name')} at {lead_info.get('company')} ({lead_info.get('job_title')})
Industry: {lead_info.get('industry')}
Dynamic Context: {dynamic_elements.get('time_reference', '')}

Company Signature:
- {company_info.get('account_email').split('@')[0]}
- {company_info.get('website')}"""