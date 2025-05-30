import logging
import asyncio
from typing import Dict, Optional, Tuple
from uuid import UUID
from openai import AsyncOpenAI
from src.config import get_settings
from datetime import datetime, timezone, timedelta
from src.database import (
    get_email_logs_reminder, 
    get_first_email_detail,
    update_reminder_sent_status,
    get_campaigns,
    get_company_by_id,
    get_lead_by_id,
    get_product_by_id,
    add_email_to_queue,
    get_email_log_by_id,
    get_campaign_by_id,
    supabase
)
from src.utils.encryption import decrypt_password
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure OpenAI
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
        "approach": "mention time-sensitive opportunity, limited availability, or market changes",
        "focus": "opportunity cost and competitive advantage",
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

def calculate_engagement_level(has_opened: bool, has_replied: bool) -> str:
    """Calculate engagement level based on email metrics"""
    if has_replied:
        return "high"
    elif has_opened:
        return "medium"
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
        elements["time_reference"] = "start of the week"
    elif current_day == "Friday":
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

async def get_enhanced_email_metrics(email_log_id: UUID) -> Dict:
    """Get email engagement metrics including has_opened status"""
    try:
        # Get the email log to check has_opened field
        response = supabase.table('email_logs')\
            .select('has_opened, has_replied')\
            .eq('id', str(email_log_id))\
            .execute()
        
        if response.data and len(response.data) > 0:
            return {
                'has_opened': response.data[0].get('has_opened', False),
                'has_replied': response.data[0].get('has_replied', False)
            }
    except Exception as e:
        logger.error(f"Error getting email metrics: {str(e)}")
    
    # Return default values if no metrics found or error occurred
    return {'has_opened': False, 'has_replied': False}

async def get_reminder_content(
    original_email_body: str,
    reminder_type: str,
    company_info: Dict,
    log: Dict,
    campaign: Dict
) -> Tuple[str, str]:
    """
    Generate enhanced reminder email content with progressive strategies
    Returns: Tuple of (subject, body)
    """
    try:
        # Get lead information
        lead_id = UUID(log['lead_id'])
        lead_info = await get_lead_by_id(lead_id)
        if not lead_info:
            logger.error(f"Lead not found: {lead_id}")
            return None, None
        
        # Get product information
        product = None
        if campaign.get('product_id'):
            product = await get_product_by_id(campaign['product_id'])
        
        # Get email metrics
        email_log_id = UUID(log['email_log_id'])
        email_metrics = await get_enhanced_email_metrics(email_log_id)
        
        # Get strategy and engagement level
        strategy = REMINDER_STRATEGIES.get(reminder_type, REMINDER_STRATEGIES[None])
        engagement_level = calculate_engagement_level(
            email_metrics['has_opened'], 
            email_metrics['has_replied']
        )        
        # Get dynamic content elements
        dynamic_elements = get_dynamic_content_elements(lead_info, reminder_type)
        
        # Adjust strategy based on engagement
        if engagement_level == "high":
            strategy["tone"] = "assumptive and action-oriented"
            strategy["approach"] = "reference their interest, be more direct"
        elif engagement_level == "none" and reminder_type in ["r2", "r3"]:
            strategy["approach"] = "try completely different angle"
        
        # Build behavioral notes
        behavioral_notes = ""
        if email_metrics['has_replied']:
            behavioral_notes = "Lead has replied - high engagement, be direct"
        elif email_metrics['has_opened']:
            behavioral_notes = "Lead has opened email - showing interest"
        else:
            behavioral_notes = "No engagement yet - try different approach"
        
        # Extract original subject
        import re
        subject_match = re.search(r'Subject: (.+?)(?:\n|$)', original_email_body)
        original_subject = subject_match.group(1) if subject_match else ""
        
        # Get product information
        product_info = ""
        enriched_data = ""
        if product:
            product_info = product.get('description', '')
            if product.get('enriched_information'):
                enriched_info = product.get('enriched_information')
                if enriched_info.get('overview'):
                    enriched_data += f"\nOverview: {enriched_info.get('overview')}"
                if enriched_info.get('key_value_proposition'):
                    enriched_data += f"\nKey Value: {enriched_info.get('key_value_proposition')}"
        
        # Get lead's enriched insights if available
        lead_insights = ""
        if lead_info.get('enriched_data'):
            try:
                if isinstance(lead_info['enriched_data'], str):
                    enriched = json.loads(lead_info['enriched_data'])
                else:
                    enriched = lead_info['enriched_data']
                
                if enriched.get('company_overview'):
                    lead_insights += f"\nCompany Overview: {enriched.get('company_overview')}"
                if enriched.get('challenges'):
                    lead_insights += f"\nChallenges: {enriched.get('challenges')}"
            except:
                pass        
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
{lead_insights}

Dynamic Elements to Consider:
- Time Context: {dynamic_elements.get('time_reference', '')}
- Role Context: {dynamic_elements.get('role_reference', '')}
- Industry Challenge: {dynamic_elements.get('industry_challenge', '')}

Behavioral Notes: {behavioral_notes}

Product Information:
{product_info}
{enriched_data}

Company Information (for signature):
- Company URL: {company_info.get('website', '')}
- Contact Person: {company_info.get('account_email', '').split('@')[0]}
- Calendar Link: {company_info.get('custom_calendar_link', '')}

Important Guidelines:
1. Generate ONLY the email body content
2. Apply the strategy tone and approach specified
3. Include relevant dynamic elements naturally
4. Reference the original email appropriately for this reminder stage
5. End with the specified CTA type
6. For high engagement: be more direct and assumptive
7. For no engagement: try a different angle if this is reminder 3-5
8. Make it feel personalized and human, not templated
9. Include proper signature with calendar link if available
10. DO NOT use placeholder values like [Your Name]"""        
        # Determine reminder number for context
        reminder_num = 1 if reminder_type is None else int(reminder_type[1]) + 1
        
        user_prompt = f"""Generate a {strategy['name']} reminder email based on the original email below.

This is reminder #{reminder_num} of 7 total reminders.

Original Email:
{original_email_body}

Remember to:
- Keep it shorter than the original email
- Apply the specified strategy and tone
- Include personalization based on lead info
- Reference dynamic elements naturally
- End with appropriate CTA
- Use proper signature format"""

        # Generate reminder content
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
        
        # Generate dynamic subject line
        subject = generate_reminder_subject(
            reminder_type,
            original_subject,
            lead_info,
            engagement_level
        )
        
        logger.info(f"Generated enhanced reminder content for email log {log['email_log_id']}")
        return subject, reminder_body.replace('\n', '<br>')
        
    except Exception as e:
        logger.error(f"Error generating enhanced reminder: {str(e)}")
        # Fallback to simple reminder
        return f"Re: {original_subject}" if original_subject else "Following up", None

def generate_reminder_subject(
    reminder_type: Optional[str],
    original_subject: str,
    lead_info: Dict,
    engagement_level: str
) -> str:
    """Generate dynamic subject line based on strategy and engagement"""
    
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
        original=original_subject or "our conversation",
        company=lead_info.get('company', 'your company'),
        first_name=lead_info.get('first_name', ''),
        industry=lead_info.get('industry', 'your industry')
    )
    
    return subject

async def send_reminder_emails(company: Dict, reminder_type: str) -> None:
    """
    Send reminder emails for a single company's campaign
    
    Args:
        company: Company data dictionary containing email credentials and settings
        reminder_type: Type of reminder to send (e.g., 'r1' for first reminder)
    """
    try:
        company_id = UUID(company['id'])
        company_info = await get_company_by_id(company_id)

        logger.info(f"Processing reminder emails for company '{company['name']}' ({company_id})")        
        # Process each email log for the company
        for log in company['logs']:
            try:
                email_log_id = UUID(log['email_log_id'])
                
                # Set the next reminder type based on current type
                if reminder_type is None:
                    next_reminder = 'r1'
                else:
                    current_num = int(reminder_type[1])
                    next_reminder = f'r{current_num + 1}'
                
                # Get the original email content
                original_email = await get_first_email_detail(email_log_id)
                if not original_email:
                    logger.warning(f"No email detail found for email log {email_log_id}")
                    continue
                
                # Get email log and campaign details
                email_log = await get_email_log_by_id(email_log_id)
                campaign = await get_campaign_by_id(email_log['campaign_id'])
                
                # Generate enhanced reminder content
                subject, reminder_content = await get_reminder_content(
                    original_email['email_body'],
                    reminder_type,
                    company_info,
                    log,
                    campaign
                )
                
                if not reminder_content:
                    logger.error(f"Failed to generate reminder content for email log {email_log_id}")
                    continue
                
                logger.info(f"Generated reminder: Subject: {subject}")
                logger.info(f"Generated reminder content preview: {reminder_content[:100]}...")

                # Add email to queue
                await add_email_to_queue(
                    company_id=campaign['company_id'],
                    campaign_id=email_log['campaign_id'],
                    campaign_run_id=email_log['campaign_run_id'],
                    lead_id=email_log['lead_id'],
                    subject=subject,
                    body=reminder_content,
                    email_log_id=email_log_id
                )                
                # Update the reminder status in database
                current_time = datetime.now(timezone.utc)
                success = await update_reminder_sent_status(
                    email_log_id=email_log_id,
                    reminder_type=next_reminder,
                    last_reminder_sent_at=current_time
                )
                if success:
                    logger.info(f"Successfully updated reminder status for log {email_log_id}")
                else:
                    logger.error(f"Failed to update reminder status for log {email_log_id}")
                
                logger.info(f"Successfully added reminder email to queue for log {email_log_id} to {log['lead_email']}")
                
            except Exception as e:
                logger.error(f"Error processing log {log['email_log_id']}: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"Error processing reminders for company {company['name']}: {str(e)}")

async def main():
    """Main function to process reminder emails for all companies"""
    try:
        page_number = 1
        while True:
            # Get campaigns with pagination
            campaigns_response = await get_campaigns(campaign_types=["email", "email_and_call"], page_number=page_number, limit=20)
            campaigns = campaigns_response['items']
            
            if not campaigns:
                break
                
            logger.info(f"Processing page {page_number} of campaigns")
            logger.info(f"Found {len(campaigns)} campaigns on this page (Total: {campaigns_response['total']})")

            for campaign in campaigns:
                logger.info(f"Processing campaign '{campaign['name']}' ({campaign['id']})")
                logger.info(f"Number of reminders: {campaign['number_of_reminders']}")
                
                # Generate reminder types dynamically based on campaign's number_of_reminders
                num_reminders = campaign.get('number_of_reminders', 0)
                if num_reminders > 7:
                    num_reminders = 7  # Cap at 7 reminders
                
                reminder_types = []
                if num_reminders > 0:
                    # Start with None for first reminder, then r1 through r6 for subsequent reminders
                    reminder_types = [None] + [f'r{i}' for i in range(1, num_reminders)]
                logger.info(f"Reminder types: {reminder_types} \n")

                # Create dynamic mapping for reminder type descriptions
                reminder_descriptions = {None: 'first'}
                for i in range(1, num_reminders):
                    if i == num_reminders - 1:  # Last reminder
                        reminder_descriptions[f'r{i}'] = f'{i+1}th and final'
                    else:
                        reminder_descriptions[f'r{i}'] = f'{i+1}th'

                # Process each reminder type
                for reminder_type in reminder_types:
                    next_reminder_type = reminder_descriptions.get(reminder_type, 'first')

                    # Process email logs with keyset pagination
                    last_id = None
                    total_processed = 0
                    
                    while True:
                        # Fetch email logs using keyset pagination
                        email_logs_response = await get_email_logs_reminder(
                            campaign['id'],
                            campaign['days_between_reminders'],
                            reminder_type,
                            last_id=last_id,
                            limit=20
                        )
                        
                        email_logs = email_logs_response['items']
                        if not email_logs:
                            break
                            
                        total_processed += len(email_logs)
                        logger.info(f"Processing batch of {len(email_logs)} email logs for {next_reminder_type} reminder (Total processed: {total_processed})")

                        # Group email logs by company for batch processing
                        company_logs = {}
                        for log in email_logs:
                            company_id = str(log['company_id'])
                            if company_id not in company_logs:
                                company_logs[company_id] = {
                                    'id': company_id,
                                    'name': log['company_name'],
                                    'account_email': log['account_email'],
                                    'account_password': log['account_password'],
                                    'account_type': log['account_type'],
                                    'logs': []
                                }
                            company_logs[company_id]['logs'].append(log)                        
                        # Process reminder for each company
                        for company_data in company_logs.values():
                            await send_reminder_emails(company_data, reminder_type)
                            
                        # Break if no more records
                        if not email_logs_response['has_more']:
                            break
                            
                        # Update cursor for next page
                        last_id = email_logs_response['last_id']
            
            # Move to next page of campaigns
            page_number += 1
            
    except Exception as e:
        logger.error(f"Error in main reminder process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())