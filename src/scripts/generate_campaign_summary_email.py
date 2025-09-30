#!/usr/bin/env python3
"""
Campaign Summary Email Generator

This script generates comprehensive campaign summary emails for ReachGenie customers.
It collects data about prospect enrichment, bounce handling, unsubscribe management,
campaign results, benchmark comparisons, and next steps information.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from src.database import (
    get_campaign_by_id,
    get_company_by_id,
    get_company_email_logs,
    get_do_not_email_list,
    get_leads_by_campaign,
    get_lead_details
)
from src.services.email_service import EmailService
from src.templates.email_templates import get_base_template

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# B2B cold email industry benchmarks
B2B_EMAIL_BENCHMARKS = {
    'open_rate': 0.215,  # 21.5% average open rate for B2B cold emails
    'response_rate': 0.075,  # 7.5% average response rate
    'meeting_rate': 0.018  # 1.8% average meeting booking rate
}

async def get_campaign_stats(campaign_id: UUID) -> Dict:
    """
    Retrieve comprehensive statistics for a campaign
    
    Args:
        campaign_id: UUID of the campaign
        
    Returns:
        Dict containing campaign statistics
    """
    campaign = await get_campaign_by_id(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found")
        
    company_id = campaign['company_id']
    
    # Get all email logs for this campaign
    email_logs = await get_company_email_logs(company_id, campaign_id)
    
    # Get all leads for this campaign
    campaign_leads = await get_leads_by_campaign(campaign_id)
    
    # Calculate stats
    total_leads = len(campaign_leads)
    total_emails_sent = len(email_logs)
    
    # Count opens, replies, and meetings
    opened_emails = sum(1 for log in email_logs if log.get('has_opened', False))
    replied_emails = sum(1 for log in email_logs if log.get('has_replied', False))
    meetings_booked = sum(1 for log in email_logs if log.get('has_meeting_booked', False))
    
    # Get do_not_email entries related to this campaign (unsubscribes, bounces)
    do_not_email_entries = await get_do_not_email_list(company_id)
    
    # Filter do_not_email entries for campaign leads
    campaign_lead_emails = [lead.get('email') for lead in campaign_leads if lead.get('email')]
    campaign_bounces = [entry for entry in do_not_email_entries.get('data', []) 
                      if entry.get('email') in campaign_lead_emails 
                      and entry.get('reason', '').lower() == 'bounce']
    
    campaign_unsubscribes = [entry for entry in do_not_email_entries.get('data', []) 
                           if entry.get('email') in campaign_lead_emails 
                           and entry.get('reason', '').lower() == 'unsubscribe']
    
    # Calculate rates
    open_rate = opened_emails / total_emails_sent if total_emails_sent > 0 else 0
    reply_rate = replied_emails / total_emails_sent if total_emails_sent > 0 else 0
    meeting_rate = meetings_booked / total_emails_sent if total_emails_sent > 0 else 0
    bounce_rate = len(campaign_bounces) / total_emails_sent if total_emails_sent > 0 else 0
    unsubscribe_rate = len(campaign_unsubscribes) / total_emails_sent if total_emails_sent > 0 else 0
    
    # Compare with industry benchmarks
    benchmark_comparison = {
        'open_rate': open_rate / B2B_EMAIL_BENCHMARKS['open_rate'] if open_rate > 0 else 0,
        'reply_rate': reply_rate / B2B_EMAIL_BENCHMARKS['response_rate'] if reply_rate > 0 else 0,
        'meeting_rate': meeting_rate / B2B_EMAIL_BENCHMARKS['meeting_rate'] if meeting_rate > 0 else 0
    }
    
    return {
        'campaign': campaign,
        'stats': {
            'total_leads': total_leads,
            'total_emails_sent': total_emails_sent,
            'opened_emails': opened_emails,
            'replied_emails': replied_emails,
            'meetings_booked': meetings_booked,
            'bounced_emails': len(campaign_bounces),
            'unsubscribed_emails': len(campaign_unsubscribes)
        },
        'rates': {
            'open_rate': open_rate,
            'reply_rate': reply_rate,
            'meeting_rate': meeting_rate,
            'bounce_rate': bounce_rate,
            'unsubscribe_rate': unsubscribe_rate
        },
        'benchmark_comparison': benchmark_comparison
    }

async def get_engaged_prospects(campaign_id: UUID, limit: int = 5) -> List[Dict]:
    """
    Get a list of engaged prospects (those who opened emails) with their enrichment data
    
    Args:
        campaign_id: UUID of the campaign
        limit: Maximum number of prospects to return
        
    Returns:
        List of enriched prospect data
    """
    campaign = await get_campaign_by_id(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found")
        
    company_id = campaign['company_id']
    
    # Get email logs for this campaign
    email_logs = await get_company_email_logs(company_id, campaign_id)
    
    # Filter to only get opened emails and sort by most recent
    opened_logs = [log for log in email_logs if log.get('has_opened', False)]
    opened_logs.sort(key=lambda x: x.get('sent_at', ''), reverse=True)
    
    # Get details for the leads who opened emails
    engaged_prospects = []
    for log in opened_logs[:limit]:
        lead_id = log.get('lead_id')
        if lead_id:
            lead_details = await get_lead_details(lead_id)
            if lead_details:
                # Extract enrichment data
                engaged_prospects.append({
                    'name': lead_details.get('name'),
                    'company': lead_details.get('company'),
                    'job_title': lead_details.get('job_title'),
                    'email': lead_details.get('email'),
                    'enriched_data': lead_details.get('enriched_data', {})
                })
    
    return engaged_prospects

async def generate_summary_email(campaign_id: UUID) -> str:
    """
    Generate a comprehensive HTML email summarizing campaign results
    
    Args:
        campaign_id: UUID of the campaign
        
    Returns:
        HTML string containing the email content
    """
    # Gather all necessary data
    campaign_stats = await get_campaign_stats(campaign_id)
    engaged_prospects = await get_engaged_prospects(campaign_id)
    
    campaign = campaign_stats['campaign']
    stats = campaign_stats['stats']
    rates = campaign_stats['rates']
    benchmark = campaign_stats['benchmark_comparison']
    
    company = await get_company_by_id(UUID(campaign['company_id']))
    
    # Format percentages
    open_rate_pct = f"{rates['open_rate'] * 100:.1f}%"
    reply_rate_pct = f"{rates['reply_rate'] * 100:.1f}%"
    meeting_rate_pct = f"{rates['meeting_rate'] * 100:.1f}%"
    bounce_rate_pct = f"{rates['bounce_rate'] * 100:.1f}%"
    unsubscribe_rate_pct = f"{rates['unsubscribe_rate'] * 100:.1f}%"
    
    # Determine if metrics are above/below benchmark
    open_rate_comparison = "above average" if benchmark['open_rate'] > 1 else "below average"
    open_rate_by = f"{abs(benchmark['open_rate'] - 1) * 100:.1f}%"
    
    # Calculate when reminders will be sent (typically 3 days after initial send)
    reminder_date = (datetime.now() + timedelta(days=3)).strftime("%B %d, %Y")
    
    # Build the email content
    content = f"""
    <h1>Campaign Results Summary: {campaign['name']}</h1>
    
    <p>Dear {company['name']} Team,</p>
    
    <p>We're excited to share the results of your ReachGenie campaign so far. Here's a comprehensive overview of what ReachGenie has accomplished for you:</p>
    
    <div class="section">
        <h2>Prospect Enrichment</h2>
        <p>ReachGenie has enriched all prospects with detailed information about their pain points and buying triggers to help you connect more effectively.</p>
        
        <h3>Examples of Engaged Prospects:</h3>
        {''.join([f"""
        <div style="margin: 15px 0; padding: 10px; border-left: 3px solid #4F46E5; background-color: #F9FAFB;">
            <p><strong>{prospect['name']}</strong> at <strong>{prospect['company']}</strong> ({prospect['job_title']})</p>
            <p><em>Pain Points & Buying Triggers:</em> {prospect.get('enriched_data', {}).get('pain_points', 'Information being gathered')}</p>
        </div>
        """ for prospect in engaged_prospects])}
    </div>
    
    <div class="section">
        <h2>Automated Email Management</h2>
        <p>ReachGenie has automatically managed your campaign to ensure optimal deliverability:</p>
        <ul>
            <li><strong>{stats['bounced_emails']} bounced emails</strong> were automatically cleaned and added to your do_not_email list</li>
            <li><strong>{stats['unsubscribed_emails']} unsubscribe requests</strong> were automatically processed and respected</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>Campaign Results</h2>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #F3F4F6;">
                <th style="padding: 10px; text-align: left; border: 1px solid #E5E7EB;">Metric</th>
                <th style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">Results</th>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #E5E7EB;">Total Emails Sent</td>
                <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">{stats['total_emails_sent']}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #E5E7EB;">Opens</td>
                <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">{stats['opened_emails']} ({open_rate_pct})</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #E5E7EB;">Replies</td>
                <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">{stats['replied_emails']} ({reply_rate_pct})</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #E5E7EB;">Meetings Booked</td>
                <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">{stats['meetings_booked']} ({meeting_rate_pct})</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #E5E7EB;">Bounces</td>
                <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">{stats['bounced_emails']} ({bounce_rate_pct})</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #E5E7EB;">Unsubscribes</td>
                <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">{stats['unsubscribed_emails']} ({unsubscribe_rate_pct})</td>
            </tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Benchmark Comparison</h2>
        <p>Your open rate of {open_rate_pct} is <strong>{open_rate_comparison}</strong> the B2B industry cold email benchmark of {B2B_EMAIL_BENCHMARKS['open_rate']*100:.1f}% by {open_rate_by}.</p>
        <div style="background-color: #F3F4F6; padding: 15px; border-radius: 5px; margin: 10px 0;">
            <p style="margin: 0;"><strong>What this means:</strong> {
                "Your campaign is performing well compared to industry standards. This indicates good targeting and relevant messaging." 
                if benchmark['open_rate'] > 1 else 
                "There may be opportunities to improve your targeting or messaging to increase engagement."
            }</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Next Steps</h2>
        <ul>
            <li>ReachGenie is currently processing <strong>{stats['total_leads']} total prospects</strong> for your campaign</li>
            <li>Reminder emails will be sent to non-responders on <strong>{reminder_date}</strong></li>
            <li>We'll continue to enrich prospect data as we gather more information about their engagement</li>
        </ul>
    </div>
    
    <p>Thank you for using ReachGenie to power your outreach efforts. If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
    
    <p>Best regards,<br>The ReachGenie Team</p>
    """
    
    # Wrap in base template
    return get_base_template(content)

async def send_campaign_summary_email(campaign_id: UUID, recipient_email: str) -> None:
    """
    Generate and send a campaign summary email
    
    Args:
        campaign_id: UUID of the campaign
        recipient_email: Email address to send the summary to
    """
    try:
        # Get campaign details
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            logger.error(f"Campaign with ID {campaign_id} not found")
            return
            
        # Generate the email content
        email_content = await generate_summary_email(campaign_id)
        
        # Send the email
        email_service = EmailService()
        
        await email_service.send_email(
            to_email=recipient_email,
            subject=f"Campaign Summary: {campaign['name']}",
            html_content=email_content
        )
        
        logger.info(f"Successfully sent campaign summary email for campaign {campaign_id} to {recipient_email}")
    
    except Exception as e:
        logger.error(f"Error sending campaign summary email: {str(e)}")

async def main(campaign_id: str, recipient_email: str):
    """
    Main function to run the script
    
    Args:
        campaign_id: String representation of campaign UUID
        recipient_email: Email address to send the summary to
    """
    try:
        # Convert string to UUID
        campaign_uuid = UUID(campaign_id)
        
        # Send the summary email
        await send_campaign_summary_email(campaign_uuid, recipient_email)
        
    except ValueError as e:
        logger.error(f"Invalid campaign ID: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python -m src.scripts.generate_campaign_summary_email <campaign_id> <recipient_email>")
        sys.exit(1)
    
    campaign_id = sys.argv[1]
    recipient_email = sys.argv[2]
    
    asyncio.run(main(campaign_id, recipient_email)) 