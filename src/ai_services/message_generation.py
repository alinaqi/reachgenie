"""
Message generation service for LinkedIn messaging
"""
from typing import Dict, Any, Optional
import logging
from src.config import get_settings
import anthropic

logger = logging.getLogger(__name__)
settings = get_settings()

class MessageGenerationService:
    """Service for generating personalized LinkedIn messages using AI"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    
    async def generate_linkedin_message(
        self,
        template: str,
        lead_data: Dict[str, Any],
        company_data: Dict[str, Any],
        insights: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a personalized LinkedIn message.
        
        Args:
            template: Message template with placeholders
            lead_data: Information about the lead
            company_data: Information about the sender's company
            insights: Additional insights about the lead's company
            
        Returns:
            Personalized message
        """
        # Build context for the AI
        context = f"""
You are helping to write a personalized LinkedIn message for B2B outreach.

SENDER COMPANY:
Name: {company_data.get('name')}
Industry: {company_data.get('industry')}
Overview: {company_data.get('overview')}
Products/Services: {company_data.get('products_services')}

RECIPIENT:
Name: {lead_data.get('name')}
Title: {lead_data.get('job_title')}
Company: {lead_data.get('company')}
Headline: {lead_data.get('linkedin_headline')}
Industry: {', '.join(lead_data.get('industries', []))}
Company Size: {lead_data.get('company_size')}
"""

        if insights:
            context += f"""
RECIPIENT COMPANY INSIGHTS:
{insights.get('summary', '')}
Recent News: {insights.get('recent_news', '')}
Challenges: {insights.get('challenges', '')}
"""

        prompt = f"""{context}

MESSAGE TEMPLATE:
{template}

Based on the template and context above, write a personalized LinkedIn message that:
1. Addresses the recipient by their first name
2. References something specific about their company or role
3. Clearly explains the value proposition
4. Includes a clear call-to-action
5. Keeps a professional but friendly tone
6. Is concise (under 300 words)

Do not use generic phrases or make it sound like a mass message.
Replace any placeholders in the template with relevant information.

Write only the message content, no explanations or metadata."""

        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            message = response.content[0].text.strip()
            return message
            
        except Exception as e:
            logger.error(f"Failed to generate LinkedIn message: {str(e)}")
            # Fallback to basic template replacement
            return self._basic_template_replacement(template, lead_data, company_data)
    
    async def generate_linkedin_invitation(
        self,
        template: str,
        lead_data: Dict[str, Any],
        company_data: Dict[str, Any],
        max_length: int = 300
    ) -> str:
        """
        Generate a personalized LinkedIn invitation message.
        
        LinkedIn invitations have a 300 character limit.
        """
        context = f"""
You are writing a LinkedIn connection invitation message.

SENDER: {company_data.get('name')}
RECIPIENT: {lead_data.get('name')} - {lead_data.get('job_title')} at {lead_data.get('company')}

TEMPLATE: {template if template else 'Write a brief, personalized invitation'}

Write a LinkedIn invitation that:
1. Is personalized to the recipient
2. Mentions a specific reason for connecting
3. Is professional and friendly
4. Is UNDER {max_length} CHARACTERS (this is critical)

Write only the message, no explanations."""

        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=100,
                temperature=0.7,
                messages=[{"role": "user", "content": context}]
            )
            
            message = response.content[0].text.strip()
            
            # Ensure it's under the character limit
            if len(message) > max_length:
                message = message[:max_length-3] + "..."
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to generate invitation: {str(e)}")
            # Fallback
            fallback = f"Hi {lead_data.get('first_name', 'there')}, I'd like to connect regarding potential synergies between {company_data.get('name')} and {lead_data.get('company')}."
            return fallback[:max_length]
    
    def _basic_template_replacement(
        self,
        template: str,
        lead_data: Dict[str, Any],
        company_data: Dict[str, Any]
    ) -> str:
        """Basic template variable replacement as fallback"""
        replacements = {
            '{lead_name}': lead_data.get('name', ''),
            '{lead_first_name}': lead_data.get('first_name', ''),
            '{lead_company}': lead_data.get('company', ''),
            '{lead_title}': lead_data.get('job_title', ''),
            '{company_name}': company_data.get('name', ''),
            '{sender_name}': company_data.get('account_email', '').split('@')[0].replace('.', ' ').title()
        }
        
        message = template
        for key, value in replacements.items():
            message = message.replace(key, value)
        
        return message

# Create singleton instance
message_generation_service = MessageGenerationService()
