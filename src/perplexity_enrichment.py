import os
import httpx
import json
import re
from typing import Dict

class PerplexityEnricher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
    async def enrich_lead_data(self, lead_data: Dict) -> Dict:
        """Enrich lead data using Perplexity API to fill in missing information."""
        # Prepare the context from existing lead data
        company_name = lead_data.get('company')
        person_name = lead_data.get('name')
        
        if not company_name or not person_name:
            print(f"Missing required data: company_name={company_name}, person_name={person_name}")
            return lead_data
            
        # Construct the query with explicit JSON formatting instructions
        query = f"""Find accurate information about {person_name} at {company_name}.
        Return ONLY a valid JSON object with these exact fields (use null if unknown):
        {{
            "email": "person's email",
            "phone_number": "phone in E.164 format",
            "job_title": "current job title",
            "company_size": "number of employees (as a number)",
            "company_revenue": "annual revenue (with currency)",
            "company_facebook": "Facebook URL",
            "company_twitter": "Twitter URL"
        }}
        
        For numeric fields (company_size), provide only digits without any commas or currency symbols.
        For revenue, you can include currency symbols and commas."""
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": "sonar",
                    "messages": [{"role": "user", "content": query}]
                }
                print(f"Sending request to Perplexity API for {person_name} at {company_name}")
                print(f"Request payload: {json.dumps(payload, indent=2)}")
                
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    print(f"Perplexity API error: Status {response.status_code}")
                    print(f"Response: {response.text}")
                    return lead_data
                    
                result = response.json()
                print(f"Raw API response: {json.dumps(result, indent=2)}")
                enriched_data = self._parse_response(result)
                
                # Update lead data with enriched information, only if fields are empty
                for key, value in enriched_data.items():
                    if not lead_data.get(key) and value and value != "null" and value.lower() != "null":
                        lead_data[key] = value
                        print(f"Updated {key} with value: {value}")
                            
                return lead_data
                
        except Exception as e:
            print(f"Error enriching lead data: {str(e)}")
            print(f"Full error details: {type(e).__name__}")
            return lead_data
            
    def _parse_response(self, response: Dict) -> Dict:
        """Parse the Perplexity API response and extract relevant information."""
        try:
            content = response['choices'][0]['message']['content']
            print(f"Content to parse: {content}")
            
            # Extract JSON from the content
            json_match = re.search(r'```json\s*({[^}]+})\s*```', content)
            if not json_match:
                json_match = re.search(r'\{[^}]+\}', content)
            
            if not json_match:
                raise ValueError("No JSON object found in response")
                
            json_str = json_match.group(1) if '```json' in content else json_match.group(0)
            
            # Function to process numeric fields
            def clean_numeric_field(field_name: str, value: str) -> str:
                if not value or value.lower() == 'null':
                    return value
                if field_name == 'company_size':
                    # Extract only digits from the string
                    digits = ''.join(c for c in value if c.isdigit())
                    return digits if digits else value
                return value

            # Parse the JSON string into a dictionary
            try:
                enriched_data = json.loads(json_str)
            except json.JSONDecodeError:
                # If parsing fails, try to clean up the numeric fields first
                json_str = re.sub(r'"company_size"\s*:\s*"?(\d+,\d+)"?', 
                                lambda m: f'"company_size": {m.group(1).replace(",", "")}',
                                json_str)
                enriched_data = json.loads(json_str)
            
            # Validate and clean the data
            cleaned_data = {
                'email': str(enriched_data.get('email', '')).strip(),
                'phone_number': str(enriched_data.get('phone_number', '')).strip(),
                'job_title': str(enriched_data.get('job_title', '')).strip(),
                'company_size': clean_numeric_field('company_size', str(enriched_data.get('company_size', ''))),
                'company_revenue': str(enriched_data.get('company_revenue', '')).strip(),
                'company_facebook': str(enriched_data.get('company_facebook', '')).strip(),
                'company_twitter': str(enriched_data.get('company_twitter', '')).strip()
            }
            
            # Remove any "null" strings or empty strings
            return {k: v for k, v in cleaned_data.items() if v and v.lower() != "null" and v != "None"}
            
        except Exception as e:
            print(f"Error parsing Perplexity response: {str(e)}")
            print(f"Response structure: {json.dumps(response, indent=2)}")
            return {} 

    async def enrich_product_data(self, company_name: str, product_url: str) -> Dict:
        """Enrich product data using Perplexity API based on the product URL."""
        if not company_name or not product_url:
            print(f"Missing required data: company_name={company_name}, product_url={product_url}")
            return {}
            
        # Construct the query with explicit JSON formatting instructions
        query = f"""You are a great researcher of companies data. Given the company named {company_name} and website {product_url}, find out detailed information about the product and return as json:

        {{
            "overview": "product / service/ company overview here", # product / service/ company overview here
            "key_value_proposition": "key value proposition here", # key value proposition here
            "pricing": "pricing information if available", # pricing information if available
            "reviews": ["review 1", "review 2", "review 3"], # list of reviews from G2 or Capterra
            "market_overview": "Overview of the market the product operates in and what customers look for", # Overview of the market the product operates in and what customers look for. Try to be as broad as possible. 
            "competitors": "List of some of the competitors" # List of some of the competitors, as well as key differentiators.
        }}
        
        Return ONLY a valid JSON object with these exact fields (use null if unknown).
        """
        
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "model": "sonar",
                    "messages": [{"role": "user", "content": query}]
                }
                print(f"Sending request to Perplexity API for product at {product_url}")
                print(f"Request payload: {json.dumps(payload, indent=2)}")
                
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    print(f"Perplexity API error: Status {response.status_code}")
                    print(f"Response: {response.text}")
                    return {}
                    
                result = response.json()
                print(f"Raw API response: {json.dumps(result, indent=2)}")
                
                # Parse the response to extract the product information
                try:
                    content = result['choices'][0]['message']['content']
                    print(f"Content to parse: {content}")
                    
                    # Extract JSON from the content
                    json_match = re.search(r'```json\s*({[^}]+})\s*```', content)
                    if not json_match:
                        json_match = re.search(r'\{[^}]+\}', content)
                    
                    if not json_match:
                        raise ValueError("No JSON object found in response")
                        
                    json_str = json_match.group(1) if '```json' in content else json_match.group(0)
                    
                    # Parse the JSON string into a dictionary
                    enriched_data = json.loads(json_str)
                    
                    # Clean and validate the data
                    cleaned_data = {
                        'overview': str(enriched_data.get('overview', '')).strip(),
                        'key_value_proposition': str(enriched_data.get('key_value_proposition', '')).strip(),
                        'pricing': str(enriched_data.get('pricing', '')).strip(),
                        'reviews': enriched_data.get('reviews', []),
                        'market_overview': str(enriched_data.get('market_overview', '')).strip(),
                        'competitors': str(enriched_data.get('competitors', '')).strip()
                    }
                    
                    # Remove any "null" strings or empty strings
                    return {k: v for k, v in cleaned_data.items() if v and (isinstance(v, list) or (v.lower() != "null" and v != "None"))}
                    
                except Exception as e:
                    print(f"Error parsing Perplexity product response: {str(e)}")
                    print(f"Response structure: {json.dumps(result, indent=2)}")
                    return {}
                
        except Exception as e:
            print(f"Error enriching product data: {str(e)}")
            print(f"Full error details: {type(e).__name__}")
            return {} 