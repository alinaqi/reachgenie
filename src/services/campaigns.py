from src.utils.encryption import decrypt_password
from src.utils.smtp_client import SMTPClient
from uuid import UUID
from src.services.email_generation import generate_company_insights, generate_email_content
from src.services.perplexity_service import perplexity_service
from src.services.call_generation import generate_call_script
from src.services.bland_calls import initiate_test_call
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

        # Create a test lead object with the fake information
        lead = {
            "id": UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder UUID
            "first_name": "John",
            "last_name": "Doe",
            "email": lead_contact,
            "company": "Atlassian",
            "website": "https://www.atlassian.com/software/jira",
            "company_description": "Jira is a software product developed by Atlassian that allows bug tracking, issue tracking and agile project management. Jira is used by a large number of clients and users globally for project, time, requirements, task, bug, change, code, test, release, sprint management."
        }
        
        # Create a list with just this test lead
        leads = [lead]
                
        logger.info(f"Created test lead with email: {lead_contact}")

        for lead in leads:
            try:
                if lead.get('email'):  # Only send if lead has email
                    logger.info(f"Processing email for test lead: {lead['email']}")
                    
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
                    
                        # Send email using SMTP client
                        try:                            
                            # Send test email
                            await smtp_client.send_email(
                                to_email=lead['email'],
                                subject=subject,  # Use generated subject
                                html_content=final_body,
                                from_name=company["name"]
                            )
                            logger.info(f"Successfully sent test email to {lead['email']}")

                        except Exception as e:
                            logger.error(f"Error sending test email: {str(e)}")
                            continue
            except Exception as e:
                logger.error(f"Failed to process test email for {lead.get('email')}: {str(e)}")
                continue

async def run_test_call_campaign(campaign: dict, company: dict, lead_contact: str):
    """Handle test call campaign processing"""
    
    # Create a test lead object with the fake information
    lead = {
        "id": UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder UUID
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": lead_contact,
        "company": "Atlassian",
        "website": "https://www.atlassian.com/software/jira",
        "company_description": "Jira is a software product developed by Atlassian that allows bug tracking, issue tracking and agile project management. Jira is used by a large number of clients and users globally for project, time, requirements, task, bug, change, code, test, release, sprint management."
    }
    
    # Create a list with just this test lead
    leads = [lead]
                
    logger.info(f"Created test lead with phone number: {lead_contact}")

    for lead in leads:
        try:
            if lead.get('phone_number'):  # Only send if lead has phone number, just a safety check here as well
                logger.info(f"Processing call for test lead: {lead['phone_number']}")
                
                # Generate company insights
                insights = await generate_company_insights(lead, perplexity_service)
                if insights:
                    # Generate personalized call script
                    call_script = await generate_call_script(lead, campaign, company, insights)
                    logger.info(f"Generated call script for lead: {lead['phone_number']}")
                    logger.info(f"Call Script: {call_script}")

                    if call_script:
                        # Initiate call with Bland AI
                        await initiate_test_call(campaign, lead, call_script, lead_contact)
                    else:
                        logger.error(f"Failed to generate test call script for lead: {lead['phone_number']}")

        except Exception as e:
            logger.error(f"Failed to process test call for {lead.get('phone_number')}: {str(e)}")
            continue