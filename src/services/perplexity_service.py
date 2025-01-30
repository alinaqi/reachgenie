from typing import Dict, Optional
import json
import logging
import httpx
from src.config import get_settings
from src.prompts.company_info_prompt import COMPANY_INFO_PROMPT

logger = logging.getLogger(__name__)

class PerplexityService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.perplexity_api_key
        self.base_url = "https://api.perplexity.ai"

    async def fetch_company_info(self, website: str) -> Optional[Dict]:
        """
        Fetch company information from the website using Perplexity API.
        
        Args:
            website: The company's website URL
            
        Returns:
            Dict containing company information or None if the request fails
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Format the prompt with the website
            prompt = COMPANY_INFO_PROMPT.format(website=website)
            
            payload = {
                "model": "mixtral-8x7b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts company information from websites."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result and "choices" in result and result["choices"]:
                        try:
                            content = result["choices"][0]["message"]["content"]
                            company_info = json.loads(content)
                            return company_info
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.error(f"Failed to parse Perplexity response: {str(e)}")
                            return None
                else:
                    logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                    return None
            
        except Exception as e:
            logger.error(f"Error fetching company info from Perplexity: {str(e)}")
            return None

# Create a singleton instance
perplexity_service = PerplexityService() 