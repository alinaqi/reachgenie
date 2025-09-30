from typing import Dict, Optional
import json
import logging
import httpx
from src.config import get_settings
from src.prompts.company_info_prompt import COMPANY_INFO_PROMPT
from src.prompts.company_insights_prompt import COMPANY_INSIGHTS_PROMPT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class PerplexityService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.perplexity_api_key
        self.base_url = "https://api.perplexity.ai"

    def _clean_json_string(self, content: str) -> str:
        """Clean and prepare the content string for JSON parsing."""
        # Remove any leading/trailing whitespace
        content = content.strip()
        
        # If the content starts with a newline or spaces before the JSON
        if not content.startswith('{'):
            try:
                content = content[content.index('{'):]
            except ValueError:
                return "{}"
        
        # If there's any text after the JSON
        if content.rfind('}') != len(content) - 1:
            try:
                content = content[:content.rfind('}') + 1]
            except ValueError:
                return "{}"
        
        return content

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
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts company information from websites. Always respond with valid JSON."
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
                            logger.info(f"Raw content from Perplexity: {content}")
                            
                            # Clean the content before parsing
                            cleaned_content = self._clean_json_string(content)
                            logger.info(f"Cleaned content: {cleaned_content}")
                            
                            company_info = json.loads(cleaned_content)
                            
                            # Ensure all required fields are present
                            required_fields = ["overview", "background", "products_services", "address", "industry"]
                            for field in required_fields:
                                if field not in company_info:
                                    company_info[field] = "Not available"
                            
                            return company_info
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.error(f"Failed to parse Perplexity response: {str(e)}")
                            logger.error(f"Problematic content: {content}")
                            return {
                                "overview": "Not available",
                                "background": "Not available",
                                "products_services": "Not available",
                                "address": "Not available",
                                "industry": "Not available"
                            }
                else:
                    logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                    return None
            
        except Exception as e:
            logger.error(f"Error fetching company info from Perplexity: {str(e)}")
            logger.exception("Full traceback:")
            return None

    async def get_company_insights(self, company_name: str, company_website: str, company_description: str, lead_title: str = "", lead_department: str = "") -> Optional[str]:
        """
        Get company insights using Perplexity API
        
        Args:
            company_name: Name of the company
            company_website: Company website URL
            company_description: Description of the company
            lead_title: Job title of the lead (optional)
            lead_department: Department of the lead (optional)
            
        Returns:
            JSON string containing company insights in a specific format
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Format the prompt with company details and lead information
            prompt = COMPANY_INSIGHTS_PROMPT.format(
                company_name=company_name,
                company_website=company_website,
                company_description=company_description,
                lead_title=lead_title,
                lead_department=lead_department
            )
            
            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a leads researcher that analyzes leads/prospects and provides detailed insights about pain points, needs, and motivations. Always respond with valid JSON in the exact format specified."
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
                            #logger.info(f"Raw content from Perplexity: {content}")
                            
                            # Enhanced content cleaning
                            content = content.strip()
                            
                            # Find the first { and last }
                            start_idx = content.find('{')
                            end_idx = content.rfind('}')
                            
                            if start_idx == -1 or end_idx == -1:
                                logger.error("No valid JSON object found in response")
                                return None
                                
                            # Extract just the JSON part
                            json_str = content[start_idx:end_idx + 1]
                            
                            # Remove any newlines or extra spaces at the start of lines
                            json_str = '\n'.join(line.strip() for line in json_str.splitlines())
                            
                            #logger.info(f"Cleaned JSON string: {json_str}")
                            
                            # Parse the JSON
                            insights_dict = json.loads(json_str)
                            
                            # Validate the structure
                            required_keys = ["businessOverview", "prospectProfessionalInterests", "painPoints", "buyingTriggers", "industryChallenges"]
                            business_overview_keys = ["companyName", "businessModel", "keyProductsServices"]
                            
                            # Check all required keys exist
                            if not all(key in insights_dict for key in required_keys):
                                logger.error(f"Missing required keys. Found keys: {list(insights_dict.keys())}")
                                raise ValueError("Missing required top-level keys")
                            
                            # Check businessOverview structure
                            if not all(key in insights_dict["businessOverview"] for key in business_overview_keys):
                                logger.error(f"Missing businessOverview keys. Found keys: {list(insights_dict['businessOverview'].keys())}")
                                raise ValueError("Missing required businessOverview keys")
                            
                            # Return validated and formatted JSON string
                            return json.dumps(insights_dict)
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {str(e)}")
                            logger.error(f"Problematic content: {content}")
                            return None
                        except ValueError as e:
                            logger.error(f"Validation error: {str(e)}")
                            return None
                        except Exception as e:
                            logger.error(f"Unexpected error while processing response: {str(e)}")
                            return None
                else:
                    logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting company insights: {str(e)}")
            logger.error(f"Full traceback:", exc_info=True)
            return None

# Create a singleton instance
perplexity_service = PerplexityService() 