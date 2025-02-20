import logging
import asyncio
import httpx
from typing import List, Dict
from uuid import UUID
from src.config import get_settings
from src.bland_client import BlandClient
from src.database import get_incomplete_calls, update_call_webhook_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def update_call_record(call_id: UUID, bland_call_id: str, bland_client: BlandClient) -> None:
    """
    Update call record with data from Bland API
    """
    try:
        # Get call details from Bland API
        async with httpx.AsyncClient() as client:
            headers = {"authorization": bland_client.api_key}
            response = await client.get(
                f"{bland_client.base_url}/v1/calls/{bland_call_id}",
                headers=headers
            )
            response.raise_for_status()
            call_data = response.json()

        # Extract relevant information
        duration = str(call_data.get("corrected_duration", 0))  # Convert to string as expected by update_call_webhook_data
        sentiment = call_data.get("analysis", {}).get("sentiment", "neutral")
        summary = call_data.get("summary", "")

        # Update the database using the existing webhook function
        result = await update_call_webhook_data(bland_call_id, duration, sentiment, summary)
        if result:
            logger.info(f"Updated call record for bland_call_id {bland_call_id} with call data")
        else:
            logger.error(f"Failed to update call record for bland_call_id {bland_call_id}")

    except Exception as e:
        logger.error(f"Error updating call record for bland_call_id {bland_call_id}: {str(e)}")

async def main():
    """
    Main function to update call stats
    """
    try:
        settings = get_settings()
        bland_client = BlandClient(api_key=settings.bland_api_key)

        # Get incomplete calls using the database function
        incomplete_calls = await get_incomplete_calls()
        logger.info(f"Found {len(incomplete_calls)} incomplete call records")

        # Update each call record
        for call in incomplete_calls:
            await update_call_record(
                call_id=UUID(call["id"]),
                bland_call_id=call["bland_call_id"],
                bland_client=bland_client
            )
            # Add a small delay to avoid overwhelming the API
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 