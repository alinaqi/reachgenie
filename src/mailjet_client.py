import httpx
from typing import Dict, List
from src.config import get_settings

class MailjetClient:
    def __init__(self, api_key: str, api_secret: str, sender_email: str, sender_name: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.base_url = "https://api.mailjet.com/v3.1"

    async def send_email(self, to_email: str, to_name: str, subject: str, html_content: str, custom_id: str) -> Dict:
        """
        Send an email using Mailjet API
        
        Args:
            to_email: Recipient's email
            to_name: Recipient's name
            subject: Email subject
            html_content: Email body in HTML format
            custom_id: Custom ID to track the email
            
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
                            "CustomID": custom_id
                        }
                    ]
                }
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Mailjet API error: {response.text}")
                
            return response.json() 