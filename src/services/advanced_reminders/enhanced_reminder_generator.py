"""
Enhanced Reminder Generator with 7-stage progression, dynamic content, and behavioral triggers
This is the main module that orchestrates all reminder generation logic
"""

import json
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

from openai import AsyncOpenAI
from src.config import get_settings
from src.database import get_lead_by_id, get_company_by_id, get_product_by_id, get_campaign_by_id

from .reminder_strategies import get_strategy, get_strategy_progression
from .dynamic_content import (
    get_time_based_greeting,
    get_day_context,
    get_seasonal_context,
    get_industry_insights,
    personalize_message_element,
    generate_dynamic_ps_line
)
from .behavioral_triggers import (
    get_behavioral_reminder_adjustments,
    get_smart_timing_recommendation,
    BehavioralAnalyzer
)

logger = logging.getLogger(__name__)
settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

class EnhancedReminderGenerator:
    """Generates highly personalized, progressive reminders with behavioral awareness"""
    
    def __init__(self, email_log: Dict, lead_data: Dict, campaign: Dict, company_info: Dict, target_reminder_type: Optional[str] = None):
        self.email_log = email_log
        self.lead_data = lead_data
        self.campaign = campaign
        self.company_info = company_info
        # If target_reminder_type is explicitly provided, use it
        # Otherwise determine from email_log
        self.reminder_type = target_reminder_type if target_reminder_type is not None else self._determine_current_reminder_type()
        self.base_strategy = get_strategy(self.reminder_type)
        self.behavioral_analyzer = BehavioralAnalyzer(email_log, lead_data)
        
    def _determine_current_reminder_type(self) -> Optional[str]:
        """Determine which reminder number we're on"""
        last_reminder = self.email_log.get('last_reminder_sent')
        
        if not last_reminder:
            return None  # First reminder
        elif last_reminder == 'r1':
            return 'r1'  # Will generate r2
        elif last_reminder == 'r2':
            return 'r2'  # Will generate r3
        # ... and so on
        else:
            # Extract number and return current state
            return last_reminder
    
    async def generate_reminder(self, original_email_body: str) -> Tuple[str, str]:
        """
        Generate a complete reminder with subject and body
        
        Returns:
            Tuple of (subject, body) for the reminder email
        """
        try:
            # Get behavioral adjustments
            adjusted_strategy = get_behavioral_reminder_adjustments(
                self.email_log,
                self.lead_data,
                self.reminder_type,
                self.base_strategy
            )
            
            # Get timing recommendations
            timing_recs = get_smart_timing_recommendation(
                self.lead_data,
                self.email_log,
                self.company_info.get('timezone', 'UTC')
            )
            
            # Get product information
            product = None
            if self.campaign.get('product_id'):
                product = await get_product_by_id(self.campaign['product_id'])
            
            # Build comprehensive context for AI
            context = self._build_reminder_context(
                original_email_body,
                adjusted_strategy,
                timing_recs,
                product
            )
            
            # Generate reminder using OpenAI
            reminder_content = await self._generate_with_ai(context)
            
            # Apply post-processing and personalization
            final_content = self._post_process_content(reminder_content)
            
            return final_content['subject'], final_content['body']
            
        except Exception as e:
            logger.error(f"Error generating enhanced reminder: {str(e)}", exc_info=True)
            logger.error(f"Reminder type: {self.reminder_type}, Strategy: {self.base_strategy.get('name', 'Unknown')}")
            # Fallback to simple reminder
            return self._generate_fallback_reminder(original_email_body)
    
    def _build_reminder_context(
        self,
        original_email: str,
        strategy: Dict,
        timing: Dict,
        product: Optional[Dict]
    ) -> Dict:
        """Build comprehensive context for AI generation"""
        
        # Get dynamic contexts
        day_context = get_day_context()
        seasonal_context = get_seasonal_context()
        industry_insights = get_industry_insights(
            self.lead_data.get('industries', ['general'])[0] if self.lead_data.get('industries') else 'general',
            self.lead_data.get('company_size', 'unknown')
        )
        
        # Determine reminder number for context
        reminder_sequence = {
            None: 1, 'r1': 2, 'r2': 3, 'r3': 4, 'r4': 5, 'r5': 6, 'r6': 7
        }
        reminder_number = reminder_sequence.get(self.reminder_type, 1)
        
        context = {
            # Strategy information
            "strategy_name": strategy['name'],
            "strategy_tone": strategy['tone'],
            "strategy_approach": strategy['approach'],
            "psychological_trigger": strategy['psychological_trigger'],
            
            # Behavioral insights
            "engagement_level": strategy['behavioral_insights']['engagement_level'],
            "days_since_sent": strategy['behavioral_insights']['days_since_sent'],
            "has_opened": self.behavioral_analyzer.has_opened,
            "has_replied": self.behavioral_analyzer.has_replied,
            "urgency_level": strategy['behavioral_insights']['urgency_level'],
            
            # Lead information
            "lead_name": self.lead_data.get('first_name', self.lead_data.get('name', '')),
            "lead_company": self.lead_data.get('company', ''),
            "lead_title": self.lead_data.get('job_title', ''),
            "lead_department": self.lead_data.get('department', ''),
            "company_size": self.lead_data.get('company_size', ''),
            
            # Dynamic content
            "time_greeting": get_time_based_greeting(),
            "day_context": day_context,
            "seasonal_context": seasonal_context,
            "industry_insights": industry_insights,
            
            # Product information
            "product_name": product.get('product_name', '') if product else '',
            "product_benefits": self._extract_product_benefits(product) if product else '',
            
            # Company signature info
            "company_name": self.company_info.get('name', ''),
            "company_website": self.company_info.get('website', ''),
            "sender_name": self.company_info.get('account_email', '').split('@')[0].replace('.', ' ').title(),
            "calendar_link": self.company_info.get('custom_calendar_link', ''),
            
            # Reminder specifics
            "reminder_number": reminder_number,
            "total_reminders": 7,
            "is_final_reminder": reminder_number == 7,
            "original_email_excerpt": self._extract_key_points(original_email),
            
            # Content options from strategy
            "opening_variations": strategy.get('opening_variations', []),
            "cta_options": strategy.get('cta_options', []),
            "value_reinforcement": strategy.get('value_reinforcement', ''),
            
            # Special instructions based on behavioral triggers
            "special_instructions": self._get_special_instructions(strategy)
        }
        
        return context
    
    def _extract_product_benefits(self, product: Dict) -> str:
        """Extract key benefits from product information"""
        if not product:
            return ""
            
        benefits = []
        
        if product.get('enriched_information'):
            enriched = product['enriched_information']
            if enriched.get('key_value_proposition'):
                benefits.append(enriched['key_value_proposition'])
            if enriched.get('ideal_icps'):
                # Match ICP to lead profile
                for icp in enriched['ideal_icps']:
                    if self._matches_icp(icp):
                        benefits.append(f"Perfect for {icp.get('description', '')}")
                        
        return " | ".join(benefits[:3])  # Top 3 benefits
    
    def _matches_icp(self, icp: Dict) -> bool:
        """Check if lead matches ideal customer profile"""
        # Simple matching logic - can be enhanced
        if icp.get('company_size') == self.lead_data.get('company_size'):
            return True
        if icp.get('industry') in self.lead_data.get('industries', []):
            return True
        return False
    
    def _extract_key_points(self, original_email: str) -> str:
        """Extract key points from original email for reference"""
        # Remove HTML tags for analysis
        import re
        clean_text = re.sub('<.*?>', '', original_email)
        
        # Extract first value proposition or key point
        lines = clean_text.split('.')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['help', 'solve', 'increase', 'reduce', 'improve']):
                return line.strip()
                
        # Fallback to first substantial line
        return lines[0].strip() if lines else ""
    
    def _get_special_instructions(self, strategy: Dict) -> str:
        """Get special instructions based on behavioral insights"""
        instructions = []
        
        if strategy.get('special_handling') == 'opened_no_reply':
            instructions.append("Acknowledge they viewed the previous email")
            
        if strategy['behavioral_insights']['engagement_level'] == 'high':
            instructions.append("Be more direct and assumptive in tone")
            
        if strategy['behavioral_insights']['urgency_level'] == 'final_attempt':
            instructions.append("This is the last attempt - be gracious and leave door open")
            
        return " | ".join(instructions)
    async def _generate_with_ai(self, context: Dict) -> Dict[str, str]:
        """Generate reminder content using OpenAI with rich context"""
        
        system_prompt = f"""You are an expert sales professional generating the {context['reminder_number']} of {context['total_reminders']} follow-up emails in a sequence.

This reminder uses the "{context['strategy_name']}" strategy with a {context['strategy_tone']} tone.
Approach: {context['strategy_approach']}
Psychological trigger: {context['psychological_trigger']}

Behavioral Context:
- Engagement level: {context['engagement_level']}
- Days since original email: {context['days_since_sent']}
- Email opened: {context['has_opened']}
- Has replied: {context['has_replied']}
- Urgency level: {context['urgency_level']}

Special Instructions: {context['special_instructions']}

Company Information (for signature):
- Company Name: {context['company_name']}
- Sender Name: {context['sender_name']}
- Company URL: {context['company_website']}
- Calendar Link: {context['calendar_link']}

Important:
1. Create natural, conversational language that doesn't feel templated
2. Reference the original email naturally: "{context['original_email_excerpt']}"
3. Use one of these opening approaches: {', '.join(context['opening_variations'][:3])}
4. Include this value reinforcement: {context['value_reinforcement']}
5. End with one of these CTAs: {', '.join(context['cta_options'][:3])}
6. DO NOT use placeholder values
7. Match the tone to the behavioral insights
8. For opened but not replied: acknowledge their interest subtly
9. Include industry-specific language when relevant
10. Make each reminder feel fresh and different from previous ones
"""

        user_prompt = f"""Generate a follow-up email for:
Lead: {context['lead_name']} at {context['lead_company']}
Role: {context['lead_title']} in {context['lead_department']}
Company Size: {context['company_size']}

Time Context: {context['time_greeting']}, {context['day_context']['day_of_week']}
Season: {context['seasonal_context']['season']} - Business Focus: {context['seasonal_context']['business_focus']}

Industry Insights:
- Common pain points: {', '.join(context['industry_insights']['pain_points'][:2])}
- Trending topics: {', '.join(context['industry_insights']['trending_topics'][:2])}

Product: {context['product_name']}
Key Benefits: {context['product_benefits']}

Create:
1. Subject line: Make it a natural reply to the original (start with "Re:" if appropriate)
   - If opened but not replied: Try a different angle
   - If not opened: Try a completely different subject approach
   
2. Email body: Natural, conversational, and personalized
   - Start with appropriate greeting and opening line
   - Reference previous conversation naturally
   - Add new value or perspective
   - Include behavioral adjustments
   - End with clear but non-pushy CTA
   - Professional signature with calendar link if available

Return as JSON with 'subject' and 'body' fields."""

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8,  # Slightly higher for more variation
                max_tokens=800
            )
            
            content = json.loads(response.choices[0].message.content)
            return content
            
        except Exception as e:
            logger.error(f"AI generation error: {str(e)}")
            raise
    
    def _post_process_content(self, ai_content: Dict[str, str]) -> Dict[str, str]:
        """Apply post-processing and final personalization"""
        
        # Add dynamic PS line if appropriate
        body = ai_content['body']
        
        # Add PS line for certain reminders
        if self.reminder_type in [None, 'r1', 'r2', 'r4']:
            ps_line = generate_dynamic_ps_line(
                self.lead_data,
                {'r1': 1, 'r2': 2, 'r4': 4}.get(self.reminder_type, 0)
            )
            if ps_line and '<br><br>PS' not in body:
                # Find the last closing before signature
                import re
                signature_pattern = r'(Best wishes|Best regards|Thanks|Regards|Sincerely)'
                match = re.search(signature_pattern, body)
                if match:
                    insert_pos = match.start()
                    body = body[:insert_pos] + f"<br><br>{ps_line}<br><br>" + body[insert_pos:]
                else:
                    # Add before the end
                    body = body.replace('</body>', f"<br><br>{ps_line}</body>")
        
        # Ensure HTML formatting
        if not body.startswith('<'):
            body = body.replace('\n', '<br>')
        
        # Add tracking pixel placeholder (will be added by email service)
        # Don't add it here as it's handled by the email sending service
        
        # Validate and clean subject
        subject = ai_content['subject'].strip()
        
        # Ensure subject is appropriate length
        if len(subject) > 100:
            subject = subject[:97] + "..."
        
        return {
            'subject': subject,
            'body': body
        }
    
    def _generate_fallback_reminder(self, original_email: str) -> Tuple[str, str]:
        """Generate simple fallback reminder if enhanced generation fails"""
        
        reminder_number = {
            None: "follow-up", 'r1': "2nd", 'r2': "3rd", 
            'r3': "4th", 'r4': "5th", 'r5': "6th", 'r6': "final"
        }.get(self.reminder_type, "follow-up")
        
        subject = f"Re: {original_email[:50]}..." if len(original_email) > 50 else f"Re: {original_email}"
        
        body = f"""Hi {self.lead_data.get('first_name', 'there')},<br><br>
I wanted to follow up on my previous email about {self.company_info.get('name', 'our solution')}.<br><br>
I understand you're busy, but I wanted to check if you had a chance to review it and if you have any questions.<br><br>
Would it make sense to have a brief conversation about how we might help {self.lead_data.get('company', 'your team')}?<br><br>
Best regards,<br>
{self.company_info.get('account_email', '').split('@')[0].replace('.', ' ').title()}<br>
{self.company_info.get('name', '')}<br>
{self.company_info.get('website', '')}
"""
        
        return subject, body

# Main function to use in the reminder sending script
async def generate_enhanced_reminder(
    email_log: Dict,
    lead_id: str,
    campaign_id: str,
    company_id: str,
    original_email_body: str,
    reminder_type: Optional[str] = None,
    campaign: Optional[Dict] = None  # Add optional campaign parameter
) -> Tuple[str, str]:
    """
    Main entry point for generating enhanced reminders
    
    Args:
        email_log: Email log data including engagement metrics
        lead_id: Lead UUID
        campaign_id: Campaign UUID  
        company_id: Company UUID
        original_email_body: Original email content
        reminder_type: Current reminder type (None, r1, r2, etc.)
        campaign: Optional campaign dict (if not provided, will fetch from DB)
        
    Returns:
        Tuple of (subject, body) for the reminder
    """
    try:
        # Fetch required data
        lead_data = await get_lead_by_id(lead_id)
        
        # Use passed campaign or fetch from DB
        if not campaign:
            campaign = await get_campaign_by_id(campaign_id)
            
        company_info = await get_company_by_id(company_id)
        
        if not all([lead_data, campaign, company_info]):
            logger.error("Missing required data for reminder generation")
            raise ValueError("Missing required data")
        
        # Create generator instance with the current state
        generator = EnhancedReminderGenerator(
            email_log=email_log,
            lead_data=lead_data,
            campaign=campaign,
            company_info=company_info,
            target_reminder_type=reminder_type  # Pass the explicit reminder type
        )
        
        # Generate reminder
        subject, body = await generator.generate_reminder(original_email_body)
        
        logger.info(f"Generated enhanced reminder for lead {lead_id}")
        logger.info(f"Reminder type: {reminder_type}, Strategy: {generator.base_strategy.get('name', 'Unknown')}")
        
        return subject, body
        
    except Exception as e:
        logger.error(f"Error in generate_enhanced_reminder: {str(e)}", exc_info=True)
        # Return simple fallback
        return "Following up", "Hi, I wanted to follow up on my previous email. Do you have any questions?"