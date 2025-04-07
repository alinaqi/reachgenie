import logging
import asyncio
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

async def update_call_record(bland_call_id: str, bland_client: BlandClient) -> None:
    """
    Update call record with data from Bland API
    """
    try:
        # Get call details using BlandClient
        call_data = await bland_client.get_call_details(bland_call_id)

        # Extract relevant information
        # Handle case where corrected_duration is None
        corrected_duration = call_data.get("corrected_duration")
        #duration = str(None if corrected_duration is None else corrected_duration)  # Convert to string as expected by update_call_webhook_data
        
        if corrected_duration is not None:
            duration = str(corrected_duration)
        else:
            duration = None
        
        # Handle the case where analysis is null
        analysis = call_data.get("analysis")
        sentiment = analysis.get("sentiment") if analysis is not None else None  # Use "neutral" instead of None to avoid conversion issues
        reminder_eligible = analysis.get("reminder_eligible") if analysis is not None else False
        summary = call_data.get("summary", "")

        transcripts = call_data.get("transcripts", [])
        recording_url = call_data.get("recording_url", "")
        error_message = call_data.get("error_message")

        # Update the database using the existing webhook function
        result = await update_call_webhook_data(bland_call_id=bland_call_id, duration=duration, sentiment=sentiment, 
                                                summary=summary, transcripts=transcripts, recording_url=recording_url, 
                                                reminder_eligible=reminder_eligible, error_message=error_message)
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
                bland_call_id=call["bland_call_id"],
                bland_client=bland_client
            )
            # Add a small delay to avoid overwhelming the API
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 