from typing import Dict, Optional
import json
import logging
from perplexity import Perplexity
from src.config import get_settings
from src.prompts.company_info_prompt import COMPANY_INFO_PROMPT

logger = logging.getLogger(__name__)

class PerplexityService:
    def __init__(self):
        settings = get_settings()
        self.client = Perplexity(api_key=settings.perplexity_api_key)

    async def fetch_company_info(self, website: str) -> Optional[Dict]:
        """
        Fetch company information from the website using Perplexity API.
        
        Args:
            website: The company's website URL
            
        Returns:
            Dict containing company information or None if the request fails
        """
        try:
            # Format the prompt with the website
            prompt = COMPANY_INFO_PROMPT.format(website=website)
            
            # Call Perplexity API
            response = await self.client.chat_completion(
                prompt=prompt,
                model="mixtral-8x7b",  # Using Mixtral model for better accuracy
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            if response and response.choices and response.choices[0].message.content:
                try:
                    company_info = json.loads(response.choices[0].message.content)
                    return company_info
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Perplexity response: {str(e)}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching company info from Perplexity: {str(e)}")
            return None

# Create a singleton instance
perplexity_service = PerplexityService() 