import httpx
from typing import Dict

class BlandClient:
    def __init__(self, api_key: str, base_url: str = "https://api.bland.ai", webhook_base_url: str = "http://localhost:8000", bland_tool_id: str = None, bland_secret_key: str = None):
        self.api_key = api_key
        self.base_url = base_url
        self.webhook_base_url = webhook_base_url
        self.bland_tool_id = bland_tool_id
        self.bland_secret_key = bland_secret_key

    async def start_call(self, phone_number: str, script: str) -> Dict:
        """
        Start an automated call using Bland AI
        
        Args:
            phone_number: The phone number to call
            script: The script for the AI to follow
            
        Returns:
            Dict containing the call details including call_id
        """

        analysis_prompt = """
        Based on the call transcript and summary, provide the two pieces of analysis:

        1. Determine the call level using the following criteria:
            0 - If the call was not connected at all
            1 - If the call went to voicemail or was not picked up
            2 - If the call was picked up but no meaningful conversation occurred (due to voice quality issues, language barriers, etc.)
            3 - If the call was picked up and had a conversation but the person showed no interest
            4 - If the call was picked up, had a conversation, and the person showed interest

        2. Analyze the sentiment:
            - For call levels 0 or 1 (not connected, voicemail, not picked up), automatically set sentiment as 'negative'
            - For connected calls (levels 2-4), determine if the overall tone and interaction was positive or negative
            
            Always return strictly 'positive' or 'negative' as the sentiment value.

        Format your response to match exactly with the schema, providing the call_level number and sentiment string.
        Note:
        - Sentiment must ALWAYS be either 'positive' or 'negative', never null or empty
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/calls",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "phone_number": phone_number,
                    "task": script,
                    "voice": "Florian",
                    "model": "enhanced",
                    "tools": [self.bland_tool_id],
                    "request_data": {
                        "bland_secret_key": self.bland_secret_key
                    },
                    "webhook": f"{self.webhook_base_url}/api/calls/webhook",
                    "analysis_prompt": analysis_prompt,
                    "analysis_schema": {
                       "call_level": "integer",
                       "sentiment": "string"
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Bland API error: {response.text}")
                
            return response.json()

    async def create_book_appointment_tool(self) -> Dict:
        """
        Create a custom tool in Bland AI for booking appointments.
        This tool will be used to handle appointment scheduling during calls.
        
        Returns:
            Dict containing the created tool details
        """
        tool_definition = {
            "name": "book_appointment",
            "description": "Book an appointment with the prospect",
            "speech": "Perfect, I'll schedule that right now, give me just a second.",
            "url": f"{self.webhook_base_url}/api/calls/book-appointment",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer {{bland_secret_key}}",
                "Content-Type": "application/json"
            },
            "body": {
                "company_uuid": "{{input.company_uuid}}",
                "email": "{{input.email}}",
                "start_time": "{{input.start_time}}",
                "email_subject": "{{input.email_subject}}"
            },
            "input_schema": {
                "example": {
                    "company_uuid": "47d4d240-7318-4db0-80hy-b7cd70c50cd4",
                    "email": "johndoe@gmail.com",
                    "start_time": "2024-01-01T00:00:00Z",
                    "email_subject": "Sales Discussion"
                },
                "type": "object",
                "properties": {
                    "company_uuid": {
                        "type": "string",
                        "description": "UUID of the company"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address of the lead/prospect",
                        "format": "email"
                    },
                    "start_time": {
                        "type": "datetime",
                        "description": "Start date and time of the appointment in ISO 8601 format"
                    },
                    "email_subject": {
                        "type": "string",
                        "description": "Subject line of the email"
                    }
                },
                "required": ["company_uuid", "email", "start_time", "email_subject"]
            },
            "response": {
                "appointment_booked": "$.message",
            },
            "timeout": 20000 # 20 seconds timeout
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/tools",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=tool_definition
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to create Bland AI tool: {response.text}")
                
            return response.json() 