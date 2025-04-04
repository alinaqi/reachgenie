import logging
import asyncio
from typing import Dict
from uuid import UUID
import json
from openai import AsyncOpenAI
from src.config import get_settings
from datetime import datetime, timezone
from src.database import (
    get_call_logs_reminder,
    update_call_reminder_sent_status,
    get_campaigns,
    get_lead_by_id,
    update_lead_enrichment,
    get_campaign_by_id,
    get_company_by_id,
    add_call_to_queue,
    get_call_by_id
)
from src.services.perplexity_service import perplexity_service
from src.services.email_generation import generate_company_insights
from src.services.call_generation import generate_call_script
from src.services.bland_calls import initiate_call

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure OpenAI
settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

async def send_reminder_calls(company: Dict, reminder_type: str) -> None:
    """
    Send reminder calls for a single company's campaign
    
    Args:
        company: Company data dictionary containing call records and settings
        reminder_type: Type of reminder to send (e.g., 'r1' for first reminder)
    """
    try:
        company_id = UUID(company['id'])
        logger.info(f"Processing reminder calls for company '{company['name']}' ({company_id})")

        # Process each call log for the company
        for log in company['logs']:
            try:
                call_log_id = UUID(log['call_log_id'])
                
                # Set the next reminder type based on current type
                # This will be used to determine the next reminder in sequence
                if reminder_type is None:
                    next_reminder = 'r1'
                else:
                    current_num = int(reminder_type[1])  # Extract number from 'r1', 'r2', etc.
                    next_reminder = f'r{current_num + 1}'

                logger.info(f"Processing call for lead: {log['lead_phone_number']}")
                
                lead_id = log['lead_id']
                lead = await get_lead_by_id(lead_id)

                # Check if lead already has enriched data
                insights = None
                if log.get('lead_enriched_data'):
                    logger.info(f"Lead {log['lead_phone_number']} already has enriched data, using existing insights")
                    # We have enriched data, use it directly
                    if isinstance(log['lead_enriched_data'], str):
                        try:
                            enriched_data = json.loads(log['lead_enriched_data'])
                            insights = json.dumps(enriched_data)
                        except json.JSONDecodeError:
                            insights = log['lead_enriched_data']
                    else:
                        insights = json.dumps(log['lead_enriched_data'])
                
                # Generate company insights if we don't have any
                if not insights:
                    logger.info(f"Generating new insights for lead: {log['lead_phone_number']}")

                    insights = await generate_company_insights(lead, perplexity_service)
                    
                    # Save the insights to the lead's enriched_data if we generated new ones
                    if insights:
                        try:
                            # Parse the insights JSON if it's a string
                            enriched_data = {}
                            if isinstance(insights, str):
                                # Try to extract JSON from the string response
                                insights_str = insights.strip()
                                # Check if the response is already in JSON format
                                try:
                                    enriched_data = json.loads(insights_str)
                                except json.JSONDecodeError:
                                    # If not, look for JSON within the string (common with LLM responses)
                                    import re
                                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```|{[\s\S]*}', insights_str)
                                    if json_match:
                                        potential_json = json_match.group(1) if json_match.group(1) else json_match.group(0)
                                        enriched_data = json.loads(potential_json)
                                    else:
                                        # If we can't extract structured JSON, store as raw text
                                        enriched_data = {"raw_insights": insights_str}
                            else:
                                enriched_data = insights
                            
                            # Update the lead with enriched data
                            await update_lead_enrichment(lead['id'], enriched_data)
                            logger.info(f"Updated lead {lead['phone_number']} with new enriched data")
                        except Exception as e:
                            logger.error(f"Error storing insights for lead {lead['phone_number']}: {str(e)}")

                if insights:
                    logger.info(f"Using insights for lead: {log['lead_phone_number']}")
                    
                    campaign_id = log['campaign_id']
                    campaign = await get_campaign_by_id(campaign_id)

                    company_obj = await get_company_by_id(company_id)
                    
                    call_obj = await get_call_by_id(call_log_id)

                    # Generate personalized call script
                    call_script = await generate_call_script(lead, campaign, company_obj, insights)
                    logger.info(f"Generated call script for lead: {lead['phone_number']}")
                    logger.info(f"Call Script: {call_script}")

                    if call_script:
                        # Initiate call with Bland AI
                        #await initiate_call(campaign=campaign, lead=lead, call_script=call_script, call_log_id=call_log_id)

                        # Add call to queue
                        await add_call_to_queue(
                            company_id=campaign['company_id'],
                            campaign_id=campaign['id'],
                            campaign_run_id=call_obj['campaign_run_id'],
                            lead_id=lead['id'],
                            call_script=call_script,
                            call_log_id=call_log_id
                        )

                        # Update the reminder status in database with current timestamp
                        current_time = datetime.now(timezone.utc)
                        success = await update_call_reminder_sent_status(
                            call_log_id=call_log_id,
                            reminder_type=next_reminder,
                            last_reminder_sent_at=current_time
                        )
                        if success:
                            logger.info(f"Successfully updated reminder status for log {call_log_id}")
                        else:
                            logger.error(f"Failed to update reminder status for log {call_log_id}")
                        
                        logger.info(f"Successfully added to queue for reminder call for log {call_log_id} to {lead['phone_number']}")
                    else:
                        logger.error(f"Failed to generate call script for lead: {lead['phone_number']}")
                
            except Exception as e:
                logger.error(f"Error processing log {log['call_log_id']}: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"Error processing reminders for company {company['name']}: {str(e)}")

async def main():
    """Main function to process reminder calls for all companies"""
    try:
        campaigns = await get_campaigns(campaign_types=["call", "email_and_call"])
        logger.info(f"Found {len(campaigns)} campaigns \n")

        for campaign in campaigns:
            logger.info(f"Processing campaign '{campaign['name']}' ({campaign['id']})")
            logger.info(f"Number of reminders: {campaign['phone_number_of_reminders']}")
            #logger.info(f"Days between reminders: {campaign['phone_days_between_reminders']}")
        
            # Generate reminder types dynamically based on campaign's phone_number_of_reminders
            num_reminders = campaign.get('phone_number_of_reminders')
            
            reminder_types = []
            if num_reminders > 0:
                reminder_types = [None] + [f'r{i}' for i in range(1, num_reminders)]

            logger.info(f"Reminder types: {reminder_types} \n")

            # Create dynamic mapping for reminder type descriptions
            reminder_descriptions = {None: 'first'}
            for i in range(1, num_reminders):
                if i == num_reminders - 1:  # Adjusted condition for last reminder
                    reminder_descriptions[f'r{i}'] = f'{i+1}th and final'
                else:
                    reminder_descriptions[f'r{i}'] = f'{i+1}th'

            # Process each reminder type
            for reminder_type in reminder_types:
                # Set the reminder type based on current type
                next_reminder_type = reminder_descriptions.get(reminder_type, 'first')

                # Fetch all call logs of the campaign that need to send reminder
                call_logs = await get_call_logs_reminder(campaign['id'], campaign['phone_days_between_reminders'], reminder_type)
                logger.info(f"Found {len(call_logs)} call logs for which the {next_reminder_type} reminder needs to be sent.")

                # Group call logs by company for batch processing
                company_logs = {}
                for log in call_logs:
                    company_id = str(log['company_id'])
                    if company_id not in company_logs:
                        company_logs[company_id] = {
                            'id': company_id,
                            'name': log['company_name'],
                            'logs': []
                        }
                    company_logs[company_id]['logs'].append(log)
                
                # Process reminder for each company
                for company_data in company_logs.values():
                    await send_reminder_calls(company_data, reminder_type)
            
    except Exception as e:
        logger.error(f"Error in main reminder process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())