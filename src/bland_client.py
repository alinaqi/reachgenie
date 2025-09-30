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
        Based on the call transcript and summary, provide the three pieces of analysis:

        1. Determine the call level using the following criteria:
            0 - If the call was not connected at all
            1 - If the call went to voicemail or was not picked up
            2 - If the call was picked up but no meaningful conversation occurred (due to voice quality issues, language barriers, etc.)
            3 - If the call was picked up and had a conversation but the person showed no interest
            4 - If the call was picked up, had a conversation, and the person showed interest

        2. Analyze the sentiment:
            - For connected calls (levels 2-4), determine if the overall tone and interaction was positive or negative

        3. Analyze the reminder eligibility:
            - For call levels 0 or 1 (not connected, voicemail, not picked up), automatically set reminder eligibility as true
            - For connected calls (levels 2-4), automatically set reminder eligibility as false

            Always return strictly 'positive', 'negative' as the sentiment value.
            Always return true or false as the reminder eligibility value.

        Format your response to match exactly with the schema, providing the call_level number, sentiment string, and reminder_eligible boolean.

        Note:
        - Sentiment must ALWAYS be either 'positive', 'negative', never null or empty.
        - Reminder eligibility must ALWAYS be true or false, never null or empty.
        """

        # Prepare request data with bland_secret_key
        call_request_data = {
            "bland_secret_key": self.bland_secret_key
        }
        # Update with additional request data if provided
        if request_data:
            call_request_data.update(request_data)

        # Log the secret key status for debugging
        if self.bland_secret_key:
            logger.info(f"Using Bland secret key: {self.bland_secret_key[:5]}...")
        else:
            logger.error("Bland secret key is None - check your .env configuration")
            # Default to the API key as a fallback - they are often the same for Bland
            self.bland_secret_key = self.api_key
            call_request_data["bland_secret_key"] = self.api_key
            logger.info("Using API key as a fallback for secret key")
            
        # Add company voice agent settings if available
        voice = "Florian"
        language = "en"
        background_track = "none"
        temperature = 0.7
        final_script = f"Your name is Josh, and you're a sales agent. You are making an outbound call to a prospect/lead.\n\n{script}"
        
        # Default values for new fields
        transfer_phone_number = None
        voice_settings = None
        noise_cancellations = None
        custom_phone_number = None
        record = True  # Default to True as per main branch

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
            # Check if bland_tool_id exists before creating the payload
            if not self.bland_tool_id:
                logger.error("Bland tool ID is None - check your .env configuration")
            
            # Prepare the request payload
            payload = {
                "phone_number": phone_number,
                "task": final_script,
                "voice": voice,
                "language": language,
                "background_track": background_track,
                "temperature": temperature,
                "model": "enhanced",
                "tools": [self.bland_tool_id] if self.bland_tool_id else [],  # Only add if it exists
                "request_data": call_request_data,
                "webhook": f"{self.webhook_base_url}/api/calls/webhook",
                "analysis_prompt": analysis_prompt,
                "analysis_schema": {
                   "call_level": "integer",
                   "sentiment": "string",
                   "reminder_eligible": "boolean"
                },
                "record": record  # Include record parameter with default value True
            }
                
            # Final verification of the request_data
            if not payload["request_data"].get("bland_secret_key"):
                logger.warning("bland_secret_key still missing in request_data, adding it directly")
                payload["request_data"]["bland_secret_key"] = self.bland_secret_key
                        
            # Add optional parameters if they exist
            if transfer_phone_number:
                payload["transfer_phone_number"] = transfer_phone_number
            if voice_settings:
                payload["voice_settings"] = voice_settings
            if noise_cancellations is not None:
                payload["noise_cancellations"] = noise_cancellations
            if custom_phone_number:
                payload["from_number"] = custom_phone_number

            # Log the final payload structure (without sensitive values)
            payload_log = payload.copy()
            if "request_data" in payload_log and "bland_secret_key" in payload_log["request_data"]:
                payload_log["request_data"]["bland_secret_key"] = "[REDACTED]"
            logger.info(f"Final API payload structure: {payload_log}")

            try:
                response = await client.post(
                    f"{self.base_url}/v1/calls",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0  # Add 30 second timeout
                )
                
                # Log detailed response information
                logger.info(f"API response status code: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"API call successful, call_id: {result.get('call_id', 'Not provided')}")
                    return result
                else:
                    # Log the error response
                    logger.error(f"Bland API error: {response.status_code}")
                    try:
                        error_detail = response.json()
                        logger.error(f"Error details: {error_detail}")
                    except Exception:
                        logger.error(f"Raw error response: {response.text}")
                    
                    # Raise a more specific exception with detailed error information
                    raise Exception(f"Bland API error: {response.status_code} - {response.text}")
                
            except httpx.RequestError as e:
                # Handle network-related errors
                logger.error(f"Network error when making Bland API call: {str(e)}")
                raise Exception(f"Network error when making Bland API call: {str(e)}")
                
            except Exception as e:
                # Handle general exceptions
                logger.error(f"Error making Bland API call: {str(e)}")
                raise

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
                "Authorization": f"Bearer {self.bland_secret_key}",
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