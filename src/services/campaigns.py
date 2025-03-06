from src.utils.encryption import decrypt_password
from src.utils.smtp_client import SMTPClient
from uuid import UUID
from main import generate_company_insights, generate_email_content
from src.services.perplexity_service import perplexity_service

import logging
logger = logging.getLogger(__name__)

async def run_test_email_campaign(campaign: dict, company: dict, lead_contact: str):
    """Handle test email campaign processing"""
    if not company.get("account_email") or not company.get("account_password"):
        logger.error(f"Company {campaign['company_id']} missing credentials")
        return
            
    if not company.get("account_type"):
        logger.error(f"Company {campaign['company_id']} missing email provider type")
        return
            
    if not company.get("name"):
        logger.error(f"Company {campaign['company_id']} missing company name")
        return    
    
    # Get campaign template
    template = campaign.get('template')
    if not template:
        logger.error(f"Campaign {campaign['id']} missing email template")
        return
    
    # Decrypt the password
    try:
        decrypted_password = decrypt_password(company["account_password"])
    except Exception as e:
        logger.error(f"Failed to decrypt email password: {str(e)}")
        return
    
    # Initialize SMTP client            
    async with SMTPClient(
        account_email=company["account_email"],
        account_password=decrypted_password,
        provider=company["account_type"]
    ) as smtp_client:
        # Get all leads having email add

        

        leads = await get_leads_with_email(campaign['id'])
        logger.info(f"Found {len(leads)} leads with emails")

        # Update campaign run with status running
        await update_campaign_run_status(
            campaign_run_id=campaign_run_id,
            status="running"
        )

        leads_processed = 0
        for lead in leads:
            try:
                if lead.get('email'):  # Only send if lead has email
                    logger.info(f"Processing email for lead: {lead['email']}")
                    
                    # Generate company insights
                    insights = await generate_company_insights(lead, perplexity_service)
                    if insights:
                        logger.info(f"Generated insights for lead: {lead['email']}")
                        
                        # Generate personalized email content
                        subject, body = await generate_email_content(lead, campaign, company, insights)
                        logger.info(f"Generated email content for lead: {lead['email']}")
                        logger.info(f"Email Subject: {subject}")
                        logger.info(f"Email Body: {body}")

                        # Replace {email_body} placeholder in template with generated body
                        final_body = template.replace("{email_body}", body)
                        body_without_tracking_pixel = final_body
                    
                        # Send email using SMTP client
                        try:
                            # Create email log first to get the ID for reply-to
                            email_log = await create_email_log(
                                campaign_id=campaign['id'],
                                lead_id=lead['id'],
                                sent_at=datetime.now(timezone.utc),
                                campaign_run_id=campaign_run_id
                            )
                            logger.info(f"Created email_log with id: {email_log['id']}")

                            # Add tracking pixel to the email body
                            final_body_with_tracking = add_tracking_pixel(final_body, email_log['id'])
                            
                            # Send email with reply-to header
                            await smtp_client.send_email(
                                to_email=lead['email'],
                                subject=subject,  # Use generated subject
                                html_content=final_body_with_tracking,  # Use template with generated body and tracking pixel
                                from_name=company["name"],
                                email_log_id=email_log['id']
                            )
                            logger.info(f"Successfully sent email to {lead['email']}")
                            
                            # Create email log detail
                            if email_log:
                                await create_email_log_detail(
                                    email_logs_id=email_log['id'],
                                    message_id=None,
                                    email_subject=subject,  # Use generated subject
                                    email_body=body_without_tracking_pixel,  # Use template with generated body without tracking pixel
                                    sender_type='assistant',
                                    sent_at=datetime.now(timezone.utc),
                                    from_name=company['name'],
                                    from_email=company['account_email'],
                                    to_email=lead['email']
                                )
                                logger.info(f"Created email log detail for email_log_id: {email_log['id']}")

                            # Update campaign run progress
                            await update_campaign_run_progress(
                                campaign_run_id=campaign_run_id,
                                leads_processed=leads_processed + 1
                            )
                            leads_processed += 1
                        except Exception as e:
                            logger.error(f"Error creating email logs: {str(e)}")
                            continue
            except Exception as e:
                logger.error(f"Failed to process email for {lead.get('email')}: {str(e)}")
                continue
        
        # Update campaign run with status completed
        await update_campaign_run_status(
            campaign_run_id=campaign_run_id,
            status="completed"
        )