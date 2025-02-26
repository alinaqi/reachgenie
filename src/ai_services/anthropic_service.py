import anthropic
import logging
from typing import Dict, Any, List, Optional
from src.config import get_settings
import uuid

logger = logging.getLogger(__name__)

class AnthropicService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Anthropic service.
        
        Args:
            api_key: Optional Anthropic API key (defaults to value from environment)
        """
        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-haiku-20241022"
        
    async def generate_ideal_customer_profile(
        self, 
        product_name: str, 
        product_description: str,
        company_info: Optional[Dict[str, Any]] = None,
        enriched_information: Optional[Dict[str, Any]] = None,
        icp_input: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple atomic ideal customer profiles for a product using Anthropic Claude.
        Each ICP focuses on a single customer type with specific attributes.
        
        Args:
            product_name: Name of the product
            product_description: Description of the product
            company_info: Optional information about the company
            enriched_information: Optional enriched information about the product
            icp_input: Optional user instructions to focus ICP generation on specific criteria
            
        Returns:
            List of dictionaries containing the generated ideal customer profiles
            
        Raises:
            Exception: If the API call fails
        """
        try:
            # Prepare context from available information
            context = f"Product Name: {product_name or 'Unnamed Product'}\n"
            context += f"Product Description: {product_description or 'No description available'}\n"
            
            if company_info:
                context += f"\nCompany Information:\n"
                # Add null checks for company info fields
                context += f"Name: {company_info.get('name', 'N/A')}\n"
                context += f"Industry: {company_info.get('industry', 'N/A')}\n"
                context += f"Overview: {company_info.get('overview', 'N/A')}\n"
            
            if enriched_information:
                context += f"\nEnriched Product Information:\n"
                if 'overview' in enriched_information:
                    context += f"Overview: {enriched_information['overview']}\n"
                if 'keyValueProposition' in enriched_information:
                    context += f"Key Value Proposition: {enriched_information['keyValueProposition']}\n"
                if 'competitors' in enriched_information:
                    context += f"Competitors: {enriched_information['competitors']}\n"
                if 'marketInfo' in enriched_information:
                    context += f"Market Information: {enriched_information['marketInfo']}\n"
            
            # Include user-provided focus instruction if provided
            user_focus = ""
            if icp_input and icp_input.strip():
                user_focus = f"\nUser-Provided Focus:\n{icp_input}\n"
            
            # Create the prompt for Anthropic Claude
            prompt = f"""Based on the following information about a product, generate at least 3 DISTINCT and ATOMIC ideal customer profiles (ICPs) in JSON format:

{context}{user_focus}

IMPORTANT GUIDELINES:
1. Each ICP must be ATOMIC - focusing on ONE SPECIFIC customer type (e.g., "VP of Sales at US Enterprise Software Companies" not "Sales Leaders in US, UK, and Germany")
2. Each ICP should target a different segment, role, or use case
3. Be specific with countries/regions - don't list multiple countries in one ICP
4. Be specific with industries - don't list multiple unrelated industries in one ICP
5. Generate at least 3 ICPs, each focusing on a different but realistic target customer{' ' if not icp_input else ''}
{f'6. Focus ICP generation on: {icp_input}' if icp_input else ''}

The ideal customer profiles should follow this structure exactly:

```json
{{
  "idealCustomerProfiles": [
    {{
      "id": "{str(uuid.uuid4())}",
      "idealCustomerProfile": {{
        "name": "Descriptive name for ICP #1",
        "companyAttributes": {{
          "industries": ["Primary Industry"],
          "companySize": {{
            "employees": {{
              "min": 50,
              "max": 1000
            }},
            "revenue": {{
              "min": 5000000,
              "max": 100000000,
              "currency": "USD"
            }}
          }},
          "geographies": {{
            "countries": ["Specific Country"],
            "regions": ["Specific Region"]
          }},
          "maturity": ["Specific Stage"],
          "funding": {{
            "hasReceivedFunding": true,
            "fundingRounds": ["Series A"]
          }},
          "technologies": ["Tech1", "Tech2"]
        }},
        "contactAttributes": {{
          "jobTitles": ["Specific Title"],
          "departments": ["Specific Department"],
          "seniority": ["Specific Level"],
          "responsibilities": ["Responsibility1", "Responsibility2"]
        }},
        "businessChallenges": ["Challenge1", "Challenge2"],
        "buyingTriggers": ["Trigger1", "Trigger2"],
        "exclusionCriteria": {{
          "industries": ["Excluded Industry1"],
          "companySize": {{
            "employees": {{
              "min": 0,
              "max": 10
            }}
          }}
        }}
      }}
    }},
    {{
      "id": "{str(uuid.uuid4())}",
      "idealCustomerProfile": {{
        "name": "Descriptive name for ICP #2",
        "companyAttributes": {{ ... }}
      }}
    }},
    {{
      "id": "{str(uuid.uuid4())}",
      "idealCustomerProfile": {{
        "name": "Descriptive name for ICP #3",
        "companyAttributes": {{ ... }}
      }}
    }}
  ]
}}
```

Make sure to:
1. Each ICP has a descriptive name that captures its SPECIFIC characteristics (e.g., "VP of Marketing at US Healthcare Companies" or "IT Directors at German Manufacturing Firms")
2. Include realistic, specific values based on the product description
3. Return at least 3 complete, distinct ICPs
4. Ensure the JSON is valid and follows the exact structure above
5. Return ONLY the JSON with no additional explanations or text
"""

            # Call Anthropic API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON content from response
            response_content = message.content[0].text
            
            # Clean up the response to extract only the JSON part
            if "```json" in response_content:
                json_content = response_content.split("```json")[1].split("```")[0].strip()
            elif "```" in response_content:
                json_content = response_content.split("```")[1].split("```")[0].strip()
            else:
                json_content = response_content.strip()
            
            # Parse the JSON
            import json
            try:
                parsed_json = json.loads(json_content)
                
                # If the structure is correct, return the list of ICPs
                if "idealCustomerProfiles" in parsed_json and isinstance(parsed_json["idealCustomerProfiles"], list):
                    icps = parsed_json["idealCustomerProfiles"]
                    
                    # Ensure each ICP has a unique ID
                    for icp in icps:
                        if "id" not in icp:
                            icp["id"] = str(uuid.uuid4())
                    
                    # Return at least 3 ICPs
                    if len(icps) < 3:
                        logger.warning(f"Generated fewer than 3 ICPs ({len(icps)}), attempting to expand")
                        # Add generic ICPs to reach the minimum of 3
                        while len(icps) < 3:
                            # Create a generic ICP with a different UUID
                            generic_icp = {
                                "id": str(uuid.uuid4()),
                                "idealCustomerProfile": {
                                    "name": f"Additional Target Customer #{len(icps) + 1}",
                                    "companyAttributes": {
                                        "industries": ["Technology"],
                                        "companySize": {
                                            "employees": {"min": 50, "max": 500},
                                            "revenue": {"min": 10000000, "max": 50000000, "currency": "USD"}
                                        },
                                        "geographies": {
                                            "countries": ["United States"],
                                            "regions": ["North America"]
                                        },
                                        "maturity": ["Growth Stage"],
                                        "funding": {
                                            "hasReceivedFunding": True,
                                            "fundingRounds": ["Series A"]
                                        },
                                        "technologies": ["Cloud", "SaaS"]
                                    },
                                    "contactAttributes": {
                                        "jobTitles": ["Director"],
                                        "departments": ["Operations"],
                                        "seniority": ["Director"],
                                        "responsibilities": ["Strategy", "Implementation"]
                                    },
                                    "businessChallenges": ["Efficiency", "Growth"],
                                    "buyingTriggers": ["Process Optimization", "Cost Reduction"],
                                    "exclusionCriteria": {
                                        "industries": ["Individual Consumers"],
                                        "companySize": {
                                            "employees": {"min": 0, "max": 10}
                                        }
                                    }
                                }
                            }
                            icps.append(generic_icp)
                    
                    return icps
                else:
                    # Try to handle other possible JSON structures
                    if "idealCustomerProfile" in parsed_json:
                        # Single ICP returned instead of a list
                        icp = {
                            "id": str(uuid.uuid4()),
                            "idealCustomerProfile": parsed_json["idealCustomerProfile"]
                        }
                        # Return as a list with 3 copies, slightly modified
                        return [
                            icp,
                            {
                                "id": str(uuid.uuid4()),
                                "idealCustomerProfile": {
                                    **icp["idealCustomerProfile"],
                                    "name": f"{icp['idealCustomerProfile'].get('name', 'ICP')} - Variant 1"
                                }
                            },
                            {
                                "id": str(uuid.uuid4()),
                                "idealCustomerProfile": {
                                    **icp["idealCustomerProfile"],
                                    "name": f"{icp['idealCustomerProfile'].get('name', 'ICP')} - Variant 2"
                                }
                            }
                        ]
                    else:
                        # Default to returning the entire parsed JSON as a single item in a list
                        logger.warning(f"Unexpected ICP JSON structure: {parsed_json}")
                        return [{
                            "id": str(uuid.uuid4()),
                            "idealCustomerProfile": parsed_json
                        }]
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                logger.error(f"Response content: {response_content}")
                # Return a default ICP structure in case of parsing error
                return [{
                    "id": str(uuid.uuid4()),
                    "idealCustomerProfile": {
                        "name": "Default ICP (JSON parsing error)",
                        "companyAttributes": {
                            "industries": ["Technology"],
                            "companySize": {
                                "employees": {"min": 50, "max": 1000},
                                "revenue": {"min": 1000000, "max": 100000000, "currency": "USD"}
                            },
                            "geographies": {
                                "countries": ["United States"],
                                "regions": ["North America"]
                            },
                            "maturity": ["Growth"],
                            "funding": {
                                "hasReceivedFunding": True,
                                "fundingRounds": ["Series A"]
                            },
                            "technologies": ["SaaS"]
                        },
                        "contactAttributes": {
                            "jobTitles": ["Manager"],
                            "departments": ["IT"],
                            "seniority": ["Manager"],
                            "responsibilities": ["Implementation"]
                        },
                        "businessChallenges": ["Efficiency"],
                        "buyingTriggers": ["Cost Reduction"],
                        "exclusionCriteria": {
                            "industries": ["Individual Consumers"],
                            "companySize": {
                                "employees": {"min": 0, "max": 5}
                            }
                        }
                    }
                }]
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise 