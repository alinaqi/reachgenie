from fastapi import HTTPException
from datetime import datetime
from typing import Dict
from src.database import (
    get_company_by_id,
    get_email_conversation_history,
    get_company_id_from_email_log,
)
from src.config import get_settings
from openai import AsyncOpenAI
import logging
from uuid import UUID
import json
from src.utils.calendar_utils import book_appointment
# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def generate_ai_reply(
    email_log_id: str,
    email_data: Dict
):
    """
    Generates a reply of the email from lead with the help of AI
    """
    settings = get_settings()
    
    # Initialize OpenAI client at the start
    client = AsyncOpenAI(api_key=settings.openai_api_key)    

    # Get the conversation history
    conversation_history = await get_email_conversation_history(email_log_id)
    logger.info(f"Found {len(conversation_history)} messages in conversation history")
    
    # Get company_id from email_log
    company_id = await get_company_id_from_email_log(email_log_id)
    if not company_id:
        raise HTTPException(status_code=400, detail="Could not find company for this conversation")
    
    # Get company to check Cronofy credentials
    company = await get_company_by_id(company_id)
    
    # Initialize functions list
    functions = []
    
    # Only add book_appointment function if company has Cronofy integration
    if company and company.get('cronofy_access_token') and company.get('cronofy_refresh_token'):
        functions.append({
            "name": "book_appointment",
            "description": """Schedule a sales meeting with the customer. Use this function when:
1. The customer explicitly asks to schedule a meeting/call
2. The customer asks about availability for a discussion
3. The customer shows strong interest in learning more and suggests a live conversation
4. The customer mentions wanting to talk to someone directly
5. The customer asks about demo or product demonstration
6. The customer expresses interest in discussing pricing or specific features in detail

The function will schedule a 30-minute meeting at the specified time.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_id": {
                        "type": "string",
                        "description": "UUID of the company - use the exact company_id provided in the system prompt"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address of the attendee - use the exact from_email provided in the system prompt"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "ISO 8601 formatted date-time string for when the meeting should start (e.g. '2024-03-20T14:30:00Z')",
                        "format": "date-time"
                    },
                    "email_subject": {
                        "type": "string",
                        "description": "Use the exact email_subject provided in the system prompt"
                    }
                },
                "required": ["company_id", "email", "start_time", "email_subject"]
            }
        })
    
    # Format conversation for OpenAI
    messages = [
        {
            "role": "system",
            "content": f"""You are an AI sales assistant. Your goal is to engage with potential customers professionally and helpfully.
            
            Guidelines for responses:
            1. Keep responses concise and focused on addressing the customer's needs and concerns
            2. If a customer expresses disinterest, acknowledge it politely and end the conversation
            3. If a customer shows interest or asks questions, provide relevant information and guide them towards the next steps
            4. When handling meeting requests:
               {
               f'''- If a customer asks for a meeting without specifying a time, ask them for their preferred date and time
               - If they only mention a date (e.g., "tomorrow" or "next week"), ask them for their preferred time
               - Only use the book_appointment function when you have both a specific date AND time
               - Use the book_appointment function with:
                 * company_id: "{str(company_id)}"
                 * email: "{email_data['from']}"
                 * email_subject: "{email_data['subject']}"
                 * start_time: the ISO 8601 formatted date-time specified by the customer''' if company and company.get('cronofy_access_token') and company.get('cronofy_refresh_token') else
               '- If a customer asks for a meeting, politely inform them that our calendar system is not currently set up and ask them to suggest a few time slots via email'
               }
            5. Always maintain a professional and courteous tone
            
            Format your responses with proper structure:
            - Start with a greeting on a new line
            - Use paragraphs to separate different points
            - Add a line break between paragraphs
            - End with a professional signature on a new line
            
            Example format:
            Hello [Name],
            
            [First point or response to their question]
            
            [Additional information or next steps if needed]
            
            Best regards,
            Sales Team"""
        }
    ]
    
    # Add conversation history
    for msg in conversation_history:
        messages.append({
            "role": msg['sender_type'],  # Use the stored sender_type
            "content": msg['email_body']
        })

    logger.info(f"OpenAI RequestMessages: {messages}")
    
    # Prepare OpenAI API call parameters
    openai_params = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    # Only include functions if we have any
    if functions:
        openai_params["functions"] = functions
        openai_params["function_call"] = "auto"
    
    # Get AI response
    response = await client.chat.completions.create(**openai_params)
    
    response_message = response.choices[0].message
    
    # Handle function calling if present
    booking_info = None
    if response_message.function_call:
        if response_message.function_call.name == "book_appointment":
            # Parse the function arguments
            function_args = json.loads(response_message.function_call.arguments)

            logger.info("Calling book_appointment function")
            
            # Call the booking function
            booking_info = await book_appointment(
                company_id=UUID(function_args["company_id"]),
                email=function_args["email"],
                start_time=datetime.fromisoformat(function_args["start_time"].replace('Z', '+00:00')),
                email_subject=function_args["email_subject"]
            )
            
            # Add the function response to the messages
            messages.append({
                "role": "function",
                "name": "book_appointment",
                "content": json.dumps(booking_info)
            })
            
            # Get the final response with the booking information
            final_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            ai_reply = final_response.choices[0].message.content.strip()
    else:
        ai_reply = response_message.content.strip()
    
    # Format AI reply with HTML
    html_template = """
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
        {}
    </div>
    """
    formatted_reply = html_template.format(ai_reply.replace('\n', '<br>'))
    
    return formatted_reply