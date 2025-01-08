import httpx
from typing import Dict, List
from src.config import get_settings
from src.database import create_email_log_detail
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

class MailjetClient:
    def __init__(self, api_key: str, api_secret: str, sender_email: str, sender_name: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.base_url = "https://api.mailjet.com/v3.1"
        self.settings = get_settings()

    async def send_email(self, to_email: str, to_name: str, subject: str, html_content: str, custom_id: str, email_log_id: UUID = None, sender_type: str = 'assistant') -> Dict:
        """
        Send an email using Mailjet API
        
        Args:
            to_email: Recipient's email
            to_name: Recipient's name
            subject: Email subject
            html_content: Email body in HTML format
            custom_id: Custom ID to track the email
            email_log_id: Optional UUID of the email_logs record to link with
            sender_type: Type of sender ('user' or 'assistant'), defaults to 'assistant'
            
        Returns:
            Dict containing the response from Mailjet
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/send",
                auth=(self.api_key, self.api_secret),
                json={
                    "Messages": [
                        {
                            "From": {
                                "Email": self.sender_email,
                                "Name": self.sender_name
                            },
                            "To": [
                                {
                                    "Email": to_email,
                                    "Name": to_name
                                }
                            ],
                            "Subject": subject,
                            "HTMLPart": html_content,
                            "CustomID": custom_id,
                            "Headers": {
                                "Reply-To": self.settings.mailjet_parse_email
                            }
                        }
                    ]
                }
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Mailjet API error: {response.text}")
            
            response_data = response.json()
            logger.info(f"Mailjet response: {response_data}")
            
            # Extract Message-ID from the response and create log detail if email_log_id is provided
            if email_log_id and response_data.get('Messages'):
                message = response_data['Messages'][0]
                logger.info(f"Message data: {message}")
                
                # Try to get Message-ID from different possible locations
                message_id = None
                if message.get('To') and len(message['To']) > 0:
                    to_data = message['To'][0]
                    if to_data.get('MessageID'):
                        message_id = str(to_data['MessageID'])
                        logger.info(f"Found MessageID: {message_id}")
                
                if message_id:
                    try:
                        logger.info(f"Creating email_log_detail with message_id: {message_id}")
                        await create_email_log_detail(
                            email_logs_id=email_log_id,
                            message_id=message_id,
                            email_subject=subject,
                            email_body=html_content,
                            sender_type=sender_type
                        )
                        logger.info("Successfully created email_log_detail")
                    except Exception as e:
                        logger.error(f"Failed to create email_log_detail: {str(e)}")
                else:
                    logger.error("No MessageID found in response")
                
            return response_data 