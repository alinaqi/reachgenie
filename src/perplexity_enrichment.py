import os
import httpx
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
            return lead_data
            
        # Construct the query
        query = f"""Find accurate information about {person_name} at {company_name}. 
        Include: job title, email, phone number, company size, company revenue, social media presence.
        Format as JSON with these fields: email, phone_number, job_title, company_size, company_revenue, company_facebook, company_twitter."""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.1-sonar-small-128k-online",
                        "messages": [{"role": "user", "content": query}]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    enriched_data = self._parse_response(result)
                    
                    # Update lead data with enriched information, only if fields are empty
                    for key, value in enriched_data.items():
                        if not lead_data.get(key) and value:
                            lead_data[key] = value
                            
                return lead_data
                
        except Exception as e:
            print(f"Error enriching lead data: {str(e)}")
            return lead_data
            
    def _parse_response(self, response: Dict) -> Dict:
        """Parse the Perplexity API response and extract relevant information."""
        try:
            content = response['choices'][0]['message']['content']
            # Assuming the response is in JSON format as requested
            import json
            enriched_data = json.loads(content)
            return {
                'email': enriched_data.get('email'),
                'phone_number': enriched_data.get('phone_number'),
                'job_title': enriched_data.get('job_title'),
                'company_size': enriched_data.get('company_size'),
                'company_revenue': enriched_data.get('company_revenue'),
                'company_facebook': enriched_data.get('company_facebook'),
                'company_twitter': enriched_data.get('company_twitter')
            }
        except Exception as e:
            print(f"Error parsing Perplexity response: {str(e)}")
            return {} 