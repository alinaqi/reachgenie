import httpx
from typing import Dict

class BlandClient:
    def __init__(self, api_key: str, base_url: str = "https://api.bland.ai"):
        self.api_key = api_key
        self.base_url = base_url

    async def start_call(self, phone_number: str, script: str) -> Dict:
        """
        Start an automated call using Bland AI
        
        Args:
            phone_number: The phone number to call
            script: The script for the AI to follow
            
        Returns:
            Dict containing the call details including call_id
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/calls",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "phone_number": phone_number,
                    "task": script,
                    "reduce_latency": True,
                    "voice_id": "josh",  # Using a default voice
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Bland API error: {response.text}")
                
            return response.json() 