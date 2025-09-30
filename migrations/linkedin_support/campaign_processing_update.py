# Update run_campaign.py to handle LinkedIn campaigns

# In the process_campaign function, add LinkedIn handling:

from src.services.linkedin_campaign_processor import linkedin_campaign_processor

async def process_campaign(campaign_run_id, campaign_id):
    """Process a campaign run"""
    # ... existing code ...
    
    # After fetching campaign and leads
    
    if campaign['type'] in ['linkedin', 'linkedin_and_email', 'linkedin_and_call', 'all_channels']:
        # Process LinkedIn messaging
        if campaign['type'] == 'linkedin' or campaign['type'] in ['linkedin_and_email', 'linkedin_and_call', 'all_channels']:
            logger.info(f"Processing LinkedIn campaign {campaign_id}")
            
            try:
                linkedin_results = await linkedin_campaign_processor.process_campaign_run(
                    campaign_run_id=campaign_run_id,
                    campaign=campaign,
                    company=company,
                    leads=leads
                )
                
                logger.info(f"LinkedIn campaign results: {linkedin_results}")
                
                # Update campaign run with LinkedIn results
                await supabase.from_('campaign_runs').update({
                    'linkedin_sent': linkedin_results['sent'],
                    'linkedin_failed': linkedin_results['failed'],
                    'linkedin_skipped': linkedin_results['skipped']
                }).eq('id', str(campaign_run_id)).execute()
                
            except Exception as e:
                logger.error(f"LinkedIn campaign processing failed: {str(e)}")
                # Continue with other channels if LinkedIn fails
    
    # Process email if needed
    if campaign['type'] in ['email', 'email_and_call', 'linkedin_and_email', 'all_channels']:
        # ... existing email processing code ...
    
    # Process calls if needed
    if campaign['type'] in ['call', 'email_and_call', 'linkedin_and_call', 'all_channels']:
        # ... existing call processing code ...
