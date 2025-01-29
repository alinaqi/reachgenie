"""
Email service module for handling all email-related functionality.
"""
from typing import List, Dict, Optional
from mailjet_rest import Client
from fastapi import HTTPException, status
from src.config import get_settings
from src.templates.email_templates import (
    get_password_reset_template,
    get_welcome_template,
    get_account_verification_template
)

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
        from_email: Optional[str] = None
    ) -> Dict:
        """
        Send an email using Mailjet.
        
        Args:
            to_email: Recipient's email address
            subject: Email subject
            html_content: HTML content of the email
            from_name: Name of the sender (default: configured mailjet_sender_name)
            from_email: Email address of the sender (default: configured mailjet_sender_email)
            
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

        try:
            response = self.client.send.create(data=data)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send email"
                )
            return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {str(e)}"
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

# Create a singleton instance
email_service = EmailService() 