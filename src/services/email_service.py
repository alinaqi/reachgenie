"""
Email service module for handling all email-related functionality.
"""
from typing import List, Dict, Optional
from mailjet_rest import Client
from fastapi import HTTPException, status
import logging
from src.config import get_settings
from src.templates.email_templates import (
    get_password_reset_template,
    get_welcome_template,
    get_account_verification_template,
    get_invite_template,
    get_company_addition_template,
    get_email_campaign_stats_template
)
from src.services.company_personalization_service import CompanyPersonalizationService
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

settings = get_settings()

class EmailService:
    def __init__(self):
        """Initialize the email service with Mailjet client"""
        self.client = Client(
            auth=(settings.mailjet_api_key, settings.mailjet_api_secret),
            version='v3.1'
        )
        self.default_sender_name = settings.mailjet_sender_name
        self.default_sender_email = settings.mailjet_sender_email

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_name: Optional[str] = None,
        from_email: Optional[str] = None,
        cc_email: Optional[str] = None
    ) -> Dict:
        """
        Send an email using Mailjet.
        
        Args:
            to_email: Recipient's email address
            subject: Email subject
            html_content: HTML content of the email
            from_name: Name of the sender (default: configured mailjet_sender_name)
            from_email: Email address of the sender (default: configured mailjet_sender_email)
            cc_email: CC recipient email address (optional)
            
        Returns:
            Dict: Response from Mailjet API
            
        Raises:
            HTTPException: If email sending fails
        """
        if not from_name:
            from_name = self.default_sender_name
        if not from_email:
            from_email = self.default_sender_email

        data = {
            'Messages': [
                {
                    "From": {
                        "Email": from_email,
                        "Name": from_name
                    },
                    "To": [
                        {
                            "Email": to_email,
                        }
                    ],
                    "Subject": subject,
                    "HTMLPart": html_content,
                }
            ]
        }

        # Add CC recipient if provided
        if cc_email:
            data['Messages'][0]['Cc'] = [
                {
                    'Email': cc_email,
                    'Name': ''
                }
            ]

        try:
            response = self.client.send.create(data=data)
            if response.status_code != 200:
                error_message = "Failed to send email"
                try:
                    error_details = response.json()
                    if isinstance(error_details, dict) and 'ErrorMessage' in error_details:
                        error_message += f": {error_details['ErrorMessage']}"
                    else:
                        error_message += f": {str(error_details)}"
                except:
                    error_message += f" (Status code: {response.status_code})"
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_message
                )
            return response.json()
        except HTTPException:
            # Re-raise HTTP exceptions as is
            raise
        except Exception as e:
            # For other exceptions, capture the full details
            error_message = f"Failed to send email: {repr(e)}"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )

    async def send_password_reset_email(self, email: str, reset_token: str) -> Dict:
        """
        Send password reset email.
        
        Args:
            email: Recipient's email address
            reset_token: Password reset token
            
        Returns:
            Dict: Response from Mailjet API
        """
        reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"
        html_content = get_password_reset_template(reset_link)
        
        return await self.send_email(
            to_email=email,
            subject="Password Reset Request",
            html_content=html_content
        )

    async def send_welcome_email(self, email: str, user_name: str) -> Dict:
        """
        Send welcome email to new users.
        
        Args:
            email: Recipient's email address
            user_name: Name of the user
            
        Returns:
            Dict: Response from Mailjet API
        """
        html_content = get_welcome_template(user_name)
        
        return await self.send_email(
            to_email=email,
            subject="Welcome to ReachGenie!",
            html_content=html_content
        )

    async def send_verification_email(self, email: str, verification_token: str) -> Dict:
        """
        Send account verification email.
        
        Args:
            email: Recipient's email address
            verification_token: Account verification token
            
        Returns:
            Dict: Response from Mailjet API
        """
        verification_link = f"{settings.frontend_url}/verify-account?token={verification_token}"
        html_content = get_account_verification_template(verification_link)
        
        return await self.send_email(
            to_email=email,
            subject="Verify Your Account",
            html_content=html_content
        )

    async def send_invite_email(
        self, 
        to_email: str, 
        company_name: str, 
        invite_token: str, 
        inviter_name: str,
        recipient_name: str = "",
        personalize: bool = True
    ) -> Dict:
        """
        Send company invite email with personalization.
        
        Args:
            to_email: Recipient's email address
            company_name: Name of the company sending invite
            invite_token: Invite token for the link
            inviter_name: Name of the person sending the invite
            recipient_name: Optional name of the recipient for personalization
            personalize: Whether to personalize the email with AI-generated content
            
        Returns:
            Dict: Response from Mailjet API
        """
        invite_link = f"{settings.frontend_url}/invite?token={invite_token}"
        
        # Initialize default personalization content
        value_proposition = ""
        engagement_tips = []
        
        # Get personalized content if requested
        if personalize:
            try:
                # Initialize the personalization service
                personalization_service = CompanyPersonalizationService()
                
                # Get company information
                company_info = await personalization_service.get_company_info(company_name)
                
                # Generate personalized value proposition
                value_proposition = await personalization_service.generate_personalized_value_proposition(company_info)
                
                # Generate engagement tips
                engagement_tips = await personalization_service.generate_engagement_tips(company_info)
                
                logger.info(f"Generated personalized content for {company_name} invite email to {to_email}")
            except Exception as e:
                logger.error(f"Error generating personalized content for invite email: {str(e)}")
                logger.exception(e)
                # Continue without personalization if there's an error
        
        # Generate the HTML content with personalization
        html_content = get_invite_template(
            company_name=company_name, 
            invite_link=invite_link, 
            inviter_name=inviter_name,
            recipient_name=recipient_name,
            value_proposition=value_proposition,
            engagement_tips=engagement_tips
        )
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Invitation to join {company_name} on ReachGenie",
            html_content=html_content
        )

    async def send_company_addition_email(self, to_email: str, user_name: str, company_name: str, inviter_name: str) -> Dict:
        """
        Send notification email to existing users when added to a company.
        
        Args:
            to_email: Recipient's email address
            user_name: Name of the user being added
            company_name: Name of the company they're being added to
            inviter_name: Name of the person who added them
            
        Returns:
            Dict: Response from Mailjet API
        """
        html_content = get_company_addition_template(user_name, company_name, inviter_name)
        
        return await self.send_email(
            to_email=to_email,
            subject=f"You've Been Added to {company_name} on ReachGenie",
            html_content=html_content
        )

    async def send_campaign_stats_email(
        self,
        to_email: str,
        campaign_name: str,
        company_name: str,
        date: str,
        emails_sent: int,
        emails_opened: int,
        emails_replied: int,
        meetings_booked: int,
        engaged_leads: List[Dict[str, str]]
    ) -> Dict:
        """
        Send campaign statistics email.
        
        Args:
            to_email: Recipient's email address
            campaign_name: Name of the campaign
            company_name: Name of the company
            date: Date for which stats are being shown (ISO format string)
            emails_sent: Number of emails sent
            emails_opened: Number of emails opened
            emails_replied: Number of emails replied to
            meetings_booked: Number of meetings booked
            engaged_leads: List of dictionaries containing lead details (name, company, job_title)
            
        Returns:
            Dict: Response from Mailjet API
        """
        html_content = get_email_campaign_stats_template(
            campaign_name=campaign_name,
            company_name=company_name,
            date=date,
            emails_sent=emails_sent,
            emails_opened=emails_opened,
            emails_replied=emails_replied,
            meetings_booked=meetings_booked,
            engaged_leads=engaged_leads
        )
        
        # Convert ISO date string to datetime and format it
        formatted_date = datetime.fromisoformat(date.replace('Z', '+00:00')).strftime("%B %d, %Y")
        
        logger.info(f"html_content: {html_content}")

        return await self.send_email(
            to_email=to_email,
            subject=f"Campaign Report: {campaign_name} - {formatted_date}",
            html_content=html_content
        )

# Create a singleton instance
email_service = EmailService() 