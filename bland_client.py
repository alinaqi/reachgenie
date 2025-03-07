import httpx
from typing import Dict
import logging
logger = logging.getLogger(__name__)

class BlandClient:
    def __init__(self, api_key: str, base_url: str = "https://api.bland.ai", webhook_base_url: str = "http://localhost:8000", bland_tool_id: str = None, bland_secret_key: str = None):
        self.api_key = api_key
        self.base_url = base_url
        self.webhook_base_url = webhook_base_url
        self.bland_tool_id = bland_tool_id
        self.bland_secret_key = bland_secret_key

    async def start_call(self, phone_number: str, script: str, request_data: Dict = None, company: Dict = None) -> Dict:
        """
        Start an automated call using Bland AI
        
        Args:
            phone_number: The phone number to call
            script: The script for the AI to follow
            request_data: Optional dictionary containing additional data for tools
            company: Company object containing company details
            
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

        # Prepare request data with bland_secret_key
        call_request_data = {
            "bland_secret_key": self.bland_secret_key
        }

        logger.info(f"bland key: {call_request_data}")
        # Update with additional request data if provided
        if request_data:
            call_request_data.update(request_data)

        # Add company voice agent settings if available
        voice = "Florian"
        language = "en"
        background_track = "none"
        temperature = 0.7
        final_script = f"Your name is Alex, and you're a sales agent. You are making an outbound call to a prospect/lead.\n\n{script}"
        
        # Default values for new fields
        transfer_phone_number = None
        voice_settings = None
        noise_cancellations = None
        custom_phone_number = None
        record = True  # Default to True (from main branch)

        if company and company.get('voice_agent_settings'):
            settings = company['voice_agent_settings']
            voice = settings.get('voice', voice)
            language = settings.get('language', language)
            background_track = settings.get('background_track', background_track)
            temperature = settings.get('temperature', temperature)
            
            # Get new optional fields
            transfer_phone_number = settings.get('transfer_phone_number')
            voice_settings = settings.get('voice_settings')
            noise_cancellations = settings.get('noise_cancellations')
            custom_phone_number = settings.get('phone_number')
            record = settings.get('record', True)  # Default to True if not specified
            
            # Prepend the prompt if available
            if settings.get('prompt'):
                final_script = f"{settings['prompt']}\n\n{script}"

        logger.info(f"Call request data: {call_request_data}")
        logger.info(f"Final script: {final_script}")

        async with httpx.AsyncClient() as client:
            # Prepare the request payload
            payload = {
                "phone_number": phone_number,
                "task": final_script,
                "voice": voice,
                "language": language,
                "background_track": background_track,
                "temperature": temperature,
                "model": "enhanced",
                "tools": [self.bland_tool_id],
                "request_data": call_request_data,
                "webhook": f"{self.webhook_base_url}/api/calls/webhook",
                "analysis_prompt": analysis_prompt,
                "analysis_schema": {
                   "call_level": "integer",
                   "sentiment": "string"
                },
                "record": record  # Include record parameter from main branch
            }
            
            # Add optional parameters if they exist
            if transfer_phone_number:
                payload["transfer_phone_number"] = transfer_phone_number
            if voice_settings:
                payload["voice_settings"] = voice_settings
            if noise_cancellations is not None:
                payload["noise_cancellations"] = noise_cancellations
            if custom_phone_number:
                payload["from_number"] = custom_phone_number
                
            response = await client.post(
                f"{self.base_url}/v1/calls",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
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
            "description": """Use this tool to schedule a meeting when the prospect agrees to book an appointment or meeting. 
            This tool will create a calendar event.
            Call this tool when:
            - The prospect explicitly agrees to schedule a meeting
            - You need to book a specific time slot for a meeting
            - The prospect wants to schedule a demo or consultation
            Do not use this tool if:
            - The prospect hasn't agreed to a meeting
            - The prospect is unsure or needs more time
            - You haven't discussed timing for the meeting""",
            "speech": "I'll help you schedule that meeting right now. please hold on for a moment.",
            "url": f"{self.webhook_base_url}/api/calls/book-appointment",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer {{bland_secret_key}}",
                "Content-Type": "application/json"
            },
            "body": {
                "company_uuid": "{{input.company_uuid}}",
                "call_log_id": "{{input.call_log_id}}",
                "email": "{{input.email}}",
                "start_time": "{{input.start_time}}",
                "email_subject": "{{input.email_subject}}"
            },
            "input_schema": {
                "example": {
                    "company_uuid": "47d4d240-7318-4db0-80hy-b7cd70c50cd4",
                    "call_log_id": "91c67842-7318-4db0-80hy-b7cd70c50cd4",
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
                    "call_log_id": {
                        "type": "string",
                        "description": "UUID of the call log"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address of the prospect",
                        "format": "email"
                    },
                    "start_time": {
                        "type": "datetime",
                        "description": "The agreed upon meeting time in ISO 8601 format (e.g., 2024-01-01T10:00:00Z). Ask the prospect for their preferred date and time."
                    },
                    "email_subject": {
                        "type": "string",
                        "description": "Subject line for the calendar invitation"
                    }
                },
                "required": ["company_uuid", "call_log_id", "email", "start_time", "email_subject"]
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

    async def get_call_details(self, call_id: str) -> Dict:
        """
        Get call details from Bland AI API
        
        Args:
            call_id: The Bland AI call ID to fetch details for
            
        Returns:
            Dict containing the call details including duration, sentiment, and summary
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        async with httpx.AsyncClient() as client:
            headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            response = await client.get(
                f"{self.base_url}/v1/calls/{call_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json() 