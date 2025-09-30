#!/usr/bin/env python3
import os
import json
import requests
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
bland_api_key = os.getenv('BLAND_API_KEY', 'org_2c46f227c0f811f82fbf4f430aa69ba67495bc996173b8e07da8f41be464c713cd964098f65e397a08ca69')
webhook_base_url = os.getenv('WEBHOOK_BASE_URL', 'https://your-webhook-url.com')

if not bland_api_key:
    logger.error("BLAND_API_KEY not found in environment variables")
    exit(1)

# Define the agent parameters
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
    "webhook": f"{webhook_base_url}/bland-webhook",
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
        "version": "1.0"
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

def create_bland_web_agent():
    """Create a Bland AI web agent for ReachGenie"""
    try:
        # API endpoint
        url = "https://api.bland.ai/v1/agents"
        
        # Headers
        headers = {
            "Content-Type": "application/json",
            "authorization": bland_api_key
        }
        
        # Make the API call
        logger.info("Creating Bland AI web agent for ReachGenie...")
        response = requests.post(url, headers=headers, data=json.dumps(agent_data))
        
        # Handle the response
        if response.status_code == 200:
            agent = response.json()
            logger.info(f"Web agent created successfully with ID: {agent.get('agent_id')}")
            logger.info(f"Response: {json.dumps(agent, indent=2)}")
            return agent
        else:
            logger.error(f"Failed to create web agent. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating web agent: {str(e)}")
        return None

if __name__ == "__main__":
    create_bland_web_agent() 