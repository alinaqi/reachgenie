#!/usr/bin/env python3
"""
Company Campaign Summary Email Generator

This script generates comprehensive campaign summary emails for ReachGenie customers,
including data for all campaigns associated with a company.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from src.database import (
    get_campaign_by_id,
    get_campaigns_by_company,
    get_company_by_id,
    get_company_email_logs,
    get_do_not_email_list,
    get_leads_by_campaign,
    get_lead_by_id
)
from src.services.email_service import EmailService
from src.templates.email_templates import get_base_template
from src.database import supabase

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

async def get_do_not_email_list_safe(company_id: UUID) -> Dict:
    """
    Wrapper for get_do_not_email_list with error handling and default values
    
    Args:
        company_id: UUID of the company
        
    Returns:
        Dict with 'data' containing do_not_email entries, or empty list on error
    """
    try:
        return await get_do_not_email_list(company_id, page=1, limit=1000)
    except Exception as e:
        logger.error(f"Error fetching do_not_email list: {str(e)}")
        return {'data': [], 'total': 0}

async def get_company_campaign_stats(company_id: UUID) -> Dict:
    """
    Retrieve comprehensive statistics for all campaigns in a company
    
    Args:
        company_id: UUID of the company
        
    Returns:
        Dict containing campaign statistics
    """
    company = await get_company_by_id(company_id)
    if not company:
        raise ValueError(f"Company with ID {company_id} not found")
        
    # Get all campaigns for this company
    campaigns = await get_campaigns_by_company(company_id)
    
    # Get all email logs for this company (across all campaigns)
    email_logs = await get_company_email_logs(company_id)
    
    # Get do_not_email entries for this company
    do_not_email_entries = await get_do_not_email_list_safe(company_id)
    
    # Get a sample of campaigns for the report
    campaign_samples = campaigns[:5] if len(campaigns) > 5 else campaigns
    
    # Get all leads for this company (using the first campaign as reference)
    all_leads = []
    if campaigns:
        all_leads = await get_leads_by_campaign(UUID(campaigns[0]['id']))
    
    # Initialize stats
    total_emails_sent = len(email_logs)
    
    # Count opens, replies, and meetings
    opened_emails = sum(1 for log in email_logs if log.get('has_opened', False))
    replied_emails = sum(1 for log in email_logs if log.get('has_replied', False))
    meetings_booked = sum(1 for log in email_logs if log.get('has_meeting_booked', False))
    
    # Get bounces and unsubscribes
    campaign_bounces = [entry for entry in do_not_email_entries.get('data', []) 
                      if entry.get('reason', '').lower() == 'bounce']
    
    campaign_unsubscribes = [entry for entry in do_not_email_entries.get('data', []) 
                           if entry.get('reason', '').lower() == 'unsubscribe']
    
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
    
    # Get campaign-specific stats
    campaign_stats = []
    for campaign in campaign_samples:
        campaign_logs = [log for log in email_logs if log.get('campaign_id') == campaign['id']]
        campaign_opens = sum(1 for log in campaign_logs if log.get('has_opened', False))
        campaign_replies = sum(1 for log in campaign_logs if log.get('has_replied', False))
        campaign_meetings = sum(1 for log in campaign_logs if log.get('has_meeting_booked', False))
        
        campaign_stats.append({
            'campaign': campaign,
            'emails_sent': len(campaign_logs),
            'opens': campaign_opens,
            'replies': campaign_replies,
            'meetings': campaign_meetings,
            'open_rate': campaign_opens / len(campaign_logs) if len(campaign_logs) > 0 else 0,
            'reply_rate': campaign_replies / len(campaign_logs) if len(campaign_logs) > 0 else 0,
            'meeting_rate': campaign_meetings / len(campaign_logs) if len(campaign_logs) > 0 else 0
        })
    
    return {
        'company': company,
        'campaigns': campaigns,
        'campaign_stats': campaign_stats,
        'stats': {
            'total_leads': len(all_leads),
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

async def get_engaged_leads(company_id: UUID, limit: int = 5) -> List[Dict]:
    """
    Get a list of engaged leads (those who opened emails) with their enrichment data
    
    Args:
        company_id: UUID of the company
        limit: Maximum number of leads to return
        
    Returns:
        List of enriched lead data
    """
    # Get email logs for this company
    email_logs = await get_company_email_logs(company_id)
    
    # Filter to only get opened emails and sort by most recent
    opened_logs = [log for log in email_logs if log.get('has_opened', False)]
    opened_logs.sort(key=lambda x: x.get('sent_at', ''), reverse=True)
    
    # Get details for the leads who opened emails
    engaged_leads = []
    seen_lead_ids = set()
    
    for log in opened_logs:
        lead_id = log.get('lead_id')
        
        if lead_id and lead_id not in seen_lead_ids and len(engaged_leads) < limit:
            seen_lead_ids.add(lead_id)
            # Get lead details and check if not soft deleted
            lead_response = supabase.table('leads')\
                .select('*')\
                .eq('id', str(lead_id))\
                .is_('deleted_at', None)\
                .execute()
            lead = lead_response.data[0] if lead_response.data else None
            
            if lead:
                # Extract enrichment data
                engaged_leads.append({
                    'name': f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                    'company': lead.get('company', 'Unknown Company'),
                    'job_title': lead.get('job_title', 'Unknown Position'),
                    'email': lead.get('email', ''),
                    'enriched_data': lead.get('enriched_data', {})
                })
    
    return engaged_leads

async def generate_company_summary_email(company_id: UUID) -> str:
    """
    Generate a comprehensive HTML email summarizing campaign results for a company
    
    Args:
        company_id: UUID of the company
        
    Returns:
        HTML string containing the email content
    """
    # Gather all necessary data
    company_stats = await get_company_campaign_stats(company_id)
    engaged_leads = await get_engaged_leads(company_id)
    
    company = company_stats['company']
    stats = company_stats['stats']
    rates = company_stats['rates']
    benchmark = company_stats['benchmark_comparison']
    campaign_stats = company_stats['campaign_stats']
    
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
    <h1>Campaign Results Summary for {company['name']}</h1>
    
    <p>Dear {company['name']} Team,</p>
    
    <p>We're excited to share the results of your ReachGenie campaigns so far. Here's a comprehensive overview of what ReachGenie has accomplished for you:</p>
    
    <div class="section">
        <h2>Prospect Enrichment</h2>
        <p>ReachGenie has enriched all prospects with detailed information about their pain points and buying triggers to help you connect more effectively.</p>
        
        <h3>Examples of Engaged Prospects:</h3>
        {''.join([f"""
        <div style="margin: 15px 0; padding: 10px; border-left: 3px solid #4F46E5; background-color: #F9FAFB;">
            <p><strong>{lead['name']}</strong> at <strong>{lead['company']}</strong> ({lead['job_title']})</p>
            <p><em>Pain Points & Buying Triggers:</em> {lead.get('enriched_data', {}).get('pain_points', 'Information being gathered')}</p>
        </div>
        """ for lead in engaged_leads])}
    </div>
    
    <div class="section">
        <h2>Automated Email Management</h2>
        <p>ReachGenie has automatically managed your campaigns to ensure optimal deliverability:</p>
        <ul>
            <li><strong>{stats['bounced_emails']} bounced emails</strong> were automatically cleaned and added to your do_not_email list</li>
            <li><strong>{stats['unsubscribed_emails']} unsubscribe requests</strong> were automatically processed and respected</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>Overall Campaign Results</h2>
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
        <h2>Campaign-Specific Results</h2>
        {''.join([f"""
        <h3>{campaign['campaign']['name']}</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 10px 0 20px 0;">
            <tr style="background-color: #F3F4F6;">
                <th style="padding: 8px; text-align: left; border: 1px solid #E5E7EB;">Metric</th>
                <th style="padding: 8px; text-align: right; border: 1px solid #E5E7EB;">Results</th>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #E5E7EB;">Emails Sent</td>
                <td style="padding: 8px; text-align: right; border: 1px solid #E5E7EB;">{campaign['emails_sent']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #E5E7EB;">Opens</td>
                <td style="padding: 8px; text-align: right; border: 1px solid #E5E7EB;">{campaign['opens']} ({campaign['open_rate'] * 100:.1f}%)</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #E5E7EB;">Replies</td>
                <td style="padding: 8px; text-align: right; border: 1px solid #E5E7EB;">{campaign['replies']} ({campaign['reply_rate'] * 100:.1f}%)</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #E5E7EB;">Meetings</td>
                <td style="padding: 8px; text-align: right; border: 1px solid #E5E7EB;">{campaign['meetings']} ({campaign['meeting_rate'] * 100:.1f}%)</td>
            </tr>
        </table>
        """ for campaign in campaign_stats])}
    </div>
    
    <div class="section">
        <h2>Benchmark Comparison</h2>
        <p>Your open rate of {open_rate_pct} is <strong>{open_rate_comparison}</strong> the B2B industry cold email benchmark of {B2B_EMAIL_BENCHMARKS['open_rate']*100:.1f}% by {open_rate_by}.</p>
        <div style="background-color: #F3F4F6; padding: 15px; border-radius: 5px; margin: 10px 0;">
            <p style="margin: 0;"><strong>What this means:</strong> {
                "Your campaigns are performing well compared to industry standards. This indicates good targeting and relevant messaging." 
                if benchmark['open_rate'] > 1 else 
                "There may be opportunities to improve your targeting or messaging to increase engagement."
            }</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Next Steps</h2>
        <ul>
            <li>ReachGenie is currently processing <strong>{stats['total_leads']} total prospects</strong> for your campaigns</li>
            <li>Reminder emails will be sent to non-responders on <strong>{reminder_date}</strong></li>
            <li>We'll continue to enrich prospect data as we gather more information about their engagement</li>
        </ul>
    </div>
    
    <p>Thank you for using ReachGenie to power your outreach efforts. If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
    
    <p>Best regards,<br>The ReachGenie Team</p>
    """
    
    # Wrap in base template
    return get_base_template(content)

async def send_company_summary_email(company_id: UUID, recipient_email: str) -> None:
    """
    Generate and send a company campaign summary email
    
    Args:
        company_id: UUID of the company
        recipient_email: Email address to send the summary to
    """
    try:
        # Get company details
        company = await get_company_by_id(company_id)
        if not company:
            logger.error(f"Company with ID {company_id} not found")
            return
            
        # Generate the email content
        email_content = await generate_company_summary_email(company_id)
        
        # Send the email
        email_service = EmailService()
        
        await email_service.send_email(
            to_email=recipient_email,
            subject=f"Campaign Summary for {company['name']}",
            html_content=email_content
        )
        
        logger.info(f"Successfully sent campaign summary email for company {company_id} to {recipient_email}")
    
    except Exception as e:
        logger.error(f"Error sending campaign summary email: {str(e)}")

async def main(company_id: str, recipient_email: str):
    """
    Main function to run the script
    
    Args:
        company_id: String representation of company UUID
        recipient_email: Email address to send the summary to
    """
    try:
        # Convert string to UUID
        company_uuid = UUID(company_id)
        
        # Send the summary email
        await send_company_summary_email(company_uuid, recipient_email)
        
    except ValueError as e:
        logger.error(f"Invalid company ID: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python -m src.scripts.generate_company_campaign_summary <company_id> <recipient_email>")
        sys.exit(1)
    
    company_id = sys.argv[1]
    recipient_email = sys.argv[2]
    
    asyncio.run(main(company_id, recipient_email)) 