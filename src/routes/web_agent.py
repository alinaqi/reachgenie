from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import json
import requests
import logging
from uuid import UUID
from src.config import get_settings
from src.auth import get_current_user
from src.models import AgentCreateResponse, WebhookResponse, WebAgentData

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/web-agent",
    tags=["web-agent"],
    responses={404: {"description": "Not found"}}
)

settings = get_settings()

@router.post("/create", response_model=AgentCreateResponse)
async def create_web_agent(
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new Bland AI web agent for ReachGenie demo.
    
    Args:
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        
    Returns:
        Dict containing the agent ID and status
    """
    try:
        # Agent configuration data
        agent_data = {
            "prompt": """
You are ReachGenie, an AI-powered sales assistant specializing in engaging prospects through personalized conversations. 
Your goal is to introduce ReachGenie's platform capabilities and schedule a demo with interested prospects.

About ReachGenie:
ReachGenie is an AI-powered sales development platform that automates personalized outreach through email and voice channels 
while maintaining authentic human-like conversations. The platform empowers sales teams to scale their outreach efforts without 
sacrificing quality, turning cold leads into warm opportunities through intelligent, contextual engagement.

Core Value Propositions:
1. Creating authentic conversations - Not just sending emails and making calls, but engaging prospects in meaningful two-way communication
2. Scaling human-quality outreach - Maintaining personalized, contextual communication at scale
3. Increasing conversion rates - Generating more meetings and opportunities through intelligent follow-up
4. Saving time for sales teams - Automating routine outreach tasks while improving quality
5. Learning and improving over time - Using AI to continuously refine messaging based on response data

Key Features to Highlight:
1. Intelligent Outreach Campaigns - Multi-touch, multi-channel campaigns that mix email and voice outreach
2. AI-Powered Email Personalization - Highly personalized emails generated for each prospect
3. Conversational Email AI - Automated, contextually relevant responses to prospect replies
4. AI Voice Calling - Natural-sounding AI voice calls with adaptive scripts
5. Intelligent Calendar Management - Automatic meeting scheduling when prospects express interest
6. Comprehensive Lead Management - Centralized lead tracking and enrichment
7. Analytics and Reporting - Real-time campaign performance tracking

Your Conversation Flow:
1. Introduce yourself and ReachGenie briefly
2. Ask about their current sales outreach processes and challenges
3. Based on their response, highlight the most relevant ReachGenie features
4. Answer any questions they have about the platform
5. If they show interest, offer to schedule a demo
6. If they want a demo, collect their email address and preferred date/time
7. Thank them for their time and confirm next steps

Always maintain a professional, helpful tone. Focus on understanding their needs rather than pushing the product. 
If they ask technical questions you can't answer, offer to connect them with a product specialist.
""",
            "voice": "lucy",  # Choose from available Bland AI voices
            "webhook": f"{settings.webhook_base_url}/api/web-agent/webhook",
            "analysis_schema": {
                "prospect_name": "string",
                "company_name": "string",
                "current_outreach_method": "string",
                "pain_points": "string",
                "interested_in_demo": "boolean",
                "email_address": "email",
                "preferred_demo_date": "YYYY-MM-DD HH:MM:SS"
            },
            "metadata": {
                "source": "reachgenie_demo",
                "version": "1.0",
                "user_id": str(current_user["id"])
            },
            "language": "ENG",
            "model": "enhanced",
            "first_sentence": "Hi there! I'm calling from ReachGenie, where we help sales teams automate personalized outreach. Do you have a few minutes to discuss how we might help your team generate more meetings with less effort?",
            "interruption_threshold": 120,
            "keywords": [
                "ReachGenie",
                "outreach",
                "personalization",
                "automation",
                "AI",
                "sales",
                "email",
                "voice"
            ],
            "max_duration": 15  # 15 minutes max call duration
        }
        
        # API endpoint
        url = "https://api.bland.ai/v1/agents"
        
        # Headers
        headers = {
            "Content-Type": "application/json",
            "authorization": settings.bland_api_key
        }
        
        # Make the API call
        response = requests.post(url, headers=headers, data=json.dumps(agent_data))
        
        # Handle the response
        if response.status_code == 200:
            agent_response = response.json()
            logger.info(f"Web agent created successfully with ID: {agent_response.get('agent_id')}")
            
            # Store agent info in database (could be done as a background task)
            # background_tasks.add_task(store_agent_data, agent_response, current_user["id"])
            
            return {
                "status": "success",
                "message": "Web agent created successfully",
                "agent_id": agent_response.get("agent_id"),
                "data": agent_response
            }
        else:
            logger.error(f"Failed to create web agent. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create web agent: {response.text}"
            )
            
    except Exception as e:
        logger.error(f"Error creating web agent: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating web agent: {str(e)}"
        )

@router.post("/webhook", response_model=WebhookResponse)
async def bland_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Webhook endpoint for Bland AI to send call data.
    
    Args:
        request: The HTTP request
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict acknowledging receipt of webhook data
    """
    try:
        # Parse webhook data
        webhook_data = await request.json()
        logger.info(f"Received webhook data from Bland AI: {json.dumps(webhook_data, indent=2)}")
        
        # Process the webhook data in the background
        # background_tasks.add_task(process_webhook_data, webhook_data)
        
        # Extract useful information from the webhook
        agent_id = webhook_data.get("agent_id")
        session_id = webhook_data.get("session_id")
        user_id = webhook_data.get("metadata", {}).get("user_id") if webhook_data.get("metadata") else None
        analysis = webhook_data.get("analysis", {})
        
        # Handle lead creation if email was provided
        if analysis and analysis.get("email_address") and analysis.get("interested_in_demo") is True:
            # background_tasks.add_task(create_lead_from_webhook, analysis, user_id)
            logger.info(f"Potential lead created from webhook: {analysis.get('email_address')}")
        
        return {
            "status": "success",
            "message": "Webhook received and processed successfully",
            "agent_id": agent_id,
            "session_id": session_id
        }
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {
            "status": "error",
            "message": f"Error processing webhook: {str(e)}"
        }

@router.get("/session-token")
async def get_session_token(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate a session token for the Bland AI web client.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dict containing the session token
    """
    try:
        # In a real implementation, this would generate a secure token
        # and possibly store it in the database
        session_token = f"demo_session_{current_user['id']}"
        
        return {
            "status": "success",
            "session_token": session_token
        }
    
    except Exception as e:
        logger.error(f"Error generating session token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating session token: {str(e)}"
        )

@router.post("/authorize/{agent_id}", response_model=Dict[str, Any])
async def authorize_agent_session(
    agent_id: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Authorize a session for a Bland AI web agent.
    
    Args:
        agent_id: The ID of the Bland web agent
        current_user: Current authenticated user
        
    Returns:
        Dict containing the session token
    """
    try:
        # API endpoint for authorizing a web agent session
        url = f"https://web.bland.ai/v1/agents/{agent_id}/authorize"
        
        # Headers
        headers = {
            "Content-Type": "application/json",
            "authorization": settings.bland_api_key
        }
        
        # Make the API call
        response = requests.post(url, headers=headers)
        
        # Handle the response
        if response.status_code == 200:
            token_data = response.json()
            logger.info(f"Session token generated successfully for agent ID: {agent_id}")
            
            return {
                "status": "success",
                "session_token": token_data.get("token"),
                "agent_id": agent_id
            }
        else:
            logger.error(f"Failed to generate session token. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate session token: {response.text}"
            )
            
    except Exception as e:
        logger.error(f"Error generating session token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating session token: {str(e)}"
        )

@router.post("/public-authorize/{agent_id}")
async def public_authorize_agent_session(
    agent_id: str
) -> Dict[str, Any]:
    """
    Public endpoint to authorize a session for a Bland AI web agent (for demo purposes).
    This endpoint doesn't require authentication and should only be used for testing.
    
    Args:
        agent_id: The ID of the Bland web agent
        
    Returns:
        Dict containing the session token
    """
    try:
        # API endpoint for authorizing a web agent session
        url = f"https://web.bland.ai/v1/agents/{agent_id}/authorize"
        
        # Headers
        headers = {
            "Content-Type": "application/json",
            "authorization": settings.bland_api_key
        }
        
        # Make the API call
        response = requests.post(url, headers=headers)
        
        # Handle the response
        if response.status_code == 200:
            token_data = response.json()
            logger.info(f"Public session token generated successfully for agent ID: {agent_id}")
            
            return {
                "status": "success",
                "session_token": token_data.get("token"),
                "agent_id": agent_id
            }
        else:
            logger.error(f"Failed to generate public session token. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate public session token: {response.text}"
            )
            
    except Exception as e:
        logger.error(f"Error generating public session token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating public session token: {str(e)}"
        ) 