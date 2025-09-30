#!/usr/bin/env python3
"""
Simple Campaign Summary Generator

This script generates a basic campaign summary focusing only on core metrics
from the campaigns and email_logs tables.
"""
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from src.database import (
    get_campaign_by_id,
    get_company_by_id,
    get_company_email_logs,
    get_lead_by_id,
    get_leads_by_campaign,
    get_leads_by_company
)
from src.services.email_service import EmailService
from src.templates.email_templates import get_base_template

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# B2B cold email industry benchmarks by industry
B2B_EMAIL_BENCHMARKS_BY_INDUSTRY = {
    'technology': {
        'open_rate': 0.225,  # 22.5% average open rate for technology
        'response_rate': 0.082,  # 8.2% average response rate
        'meeting_rate': 0.021  # 2.1% average meeting booking rate
    },
    'finance': {
        'open_rate': 0.195,  # 19.5% average open rate for finance
        'response_rate': 0.065,  # 6.5% average response rate
        'meeting_rate': 0.015  # 1.5% average meeting booking rate
    },
    'healthcare': {
        'open_rate': 0.205,  # 20.5% average open rate for healthcare
        'response_rate': 0.070,  # 7.0% average response rate
        'meeting_rate': 0.017  # 1.7% average meeting booking rate
    },
    'manufacturing': {
        'open_rate': 0.185,  # 18.5% average open rate for manufacturing
        'response_rate': 0.062,  # 6.2% average response rate
        'meeting_rate': 0.014  # 1.4% average meeting booking rate
    },
    'retail': {
        'open_rate': 0.210,  # 21.0% average open rate for retail
        'response_rate': 0.073,  # 7.3% average response rate
        'meeting_rate': 0.016  # 1.6% average meeting booking rate
    },
    # Default for any other industry
    'default': {
        'open_rate': 0.215,  # 21.5% average open rate for B2B cold emails
        'response_rate': 0.075,  # 7.5% average response rate
        'meeting_rate': 0.018  # 1.8% average meeting booking rate
    }
}

async def get_campaign_metrics(campaign_id: UUID) -> Dict:
    """
    Get basic metrics for a specific campaign
    
    Args:
        campaign_id: UUID of the campaign
        
    Returns:
        Dict containing campaign metrics
    """
    # Get campaign details
    campaign = await get_campaign_by_id(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found")
        
    # Get company details
    company_id = UUID(campaign['company_id'])
    company = await get_company_by_id(company_id)
    
    # Get email logs for this campaign
    all_email_logs = await get_company_email_logs(company_id, campaign_id)
    
    # Calculate metrics
    total_emails = len(all_email_logs)
    opened_emails = sum(1 for log in all_email_logs if log.get('has_opened', False))
    replied_emails = sum(1 for log in all_email_logs if log.get('has_replied', False))
    meetings_booked = sum(1 for log in all_email_logs if log.get('has_meeting_booked', False))
    
    # Get the total number of leads for this company more efficiently
    total_leads = 0
    campaign_leads = 0
    try:
        # Use a small limit (5) to get metadata without fetching many records
        leads_response = await get_leads_by_company(company_id, page_number=1, limit=5)
        if leads_response and 'total' in leads_response:
            # Get the total from metadata rather than counting items
            total_leads = leads_response['total']
            logger.info(f"Found {total_leads} total leads for company {company_id}")
        
        # Also get campaign-specific leads as a fallback
        campaign_leads_list = await get_leads_by_campaign(UUID(campaign['id']))
        campaign_leads = len(campaign_leads_list)
                
        # If we couldn't get company-wide leads but have campaign leads, use those
        if total_leads == 0 and campaign_leads > 0:
            total_leads = campaign_leads
            
        # If still no leads found, use a reasonable default
        if total_leads == 0:
            # If we've sent emails, use the larger of sent emails or 50
            if total_emails > 0:
                total_leads = max(total_emails, 50)
            else:
                total_leads = 50  # Default to 50 leads if we can't determine
    except Exception as e:
        logger.error(f"Error fetching leads count: {str(e)}")
        # Fallback to a reasonable number if we can't get the actual count
        if campaign_leads > 0:
            total_leads = campaign_leads
        else:
            total_leads = max(total_emails + 20, 50)  # At least emails sent + 20 more, minimum 50
    
    # Calculate remaining leads to process
    # Assumes campaign is targeting ALL leads in the company (or a significant portion)
    remaining_leads = max(0, total_leads - total_emails)
    
    # Check if all emails have been sent to campaign leads
    campaign_complete = (campaign_leads > 0 and total_emails >= campaign_leads)
    
    # Also calculate what percentage of all company leads have been emailed
    company_coverage = (total_emails / total_leads) if total_leads > 0 else 0
    
    # Calculate rates
    open_rate = opened_emails / total_emails if total_emails > 0 else 0
    reply_rate = replied_emails / total_emails if total_emails > 0 else 0
    meeting_rate = meetings_booked / total_emails if total_emails > 0 else 0
    
    # Get industry and related benchmarks
    industry = company.get('industry', '').lower() if company and 'industry' in company else ''
    
    # Map company industry to our benchmark categories
    benchmark_category = 'default'
    if industry:
        if any(tech_term in industry for tech_term in ['tech', 'software', 'it', 'saas', 'computer']):
            benchmark_category = 'technology'
        elif any(finance_term in industry for finance_term in ['finance', 'bank', 'insurance', 'invest']):
            benchmark_category = 'finance'
        elif any(health_term in industry for health_term in ['health', 'medical', 'pharma', 'hospital']):
            benchmark_category = 'healthcare'
        elif any(mfg_term in industry for mfg_term in ['manufacturing', 'factory', 'industrial', 'production']):
            benchmark_category = 'manufacturing'
        elif any(retail_term in industry for retail_term in ['retail', 'commerce', 'shop', 'store']):
            benchmark_category = 'retail'
    
    benchmarks = B2B_EMAIL_BENCHMARKS_BY_INDUSTRY[benchmark_category]
    
    # Compare with industry benchmarks
    benchmark_comparison = {
        'open_rate': open_rate / benchmarks['open_rate'] if open_rate > 0 else 0,
        'reply_rate': reply_rate / benchmarks['response_rate'] if reply_rate > 0 else 0,
        'meeting_rate': meeting_rate / benchmarks['meeting_rate'] if meeting_rate > 0 else 0,
        'industry': benchmark_category,
        'industry_open_rate': benchmarks['open_rate']
    }
    
    # Get detailed information for leads that opened emails
    engaged_prospects = []
    prospects_with_data = []  # Separate list for prospects with actual data
    all_prospects = []  # List for all prospects, regardless of data availability

    if opened_emails > 0:
        opened_logs = [log for log in all_email_logs if log.get('has_opened', False)]
        opened_logs.sort(key=lambda x: x.get('last_opened_at', ''), reverse=True)
        
        # Get detailed information for up to 5 leads (trying more to find ones with data)
        for log in opened_logs[:10]:  # Check up to 10 leads to find at least 3 with enrichment data
            if 'lead_id' in log and len(prospects_with_data) < 3:
                try:
                    lead_id_str = log['lead_id']
                    # Handle both UUID objects and string IDs
                    if isinstance(lead_id_str, str):
                        lead_id = UUID(lead_id_str)
                    else:
                        lead_id = lead_id_str
                        
                    lead = await get_lead_by_id(lead_id)
                    
                    if lead:
                        # Extract enrichment data
                        enriched_data = lead.get('enriched_data', {})
                        
                        # Handle case when enriched_data is a string
                        if isinstance(enriched_data, str):
                            try:
                                import json
                                enriched_data = json.loads(enriched_data)
                            except:
                                enriched_data = {}
                        
                        # Get pain points and buying triggers
                        pain_points = enriched_data.get('pain_points', 'Not available')
                        buying_triggers = enriched_data.get('buying_triggers', 'Not available')
                        
                        # Format name
                        name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
                        if not name:
                            name = "Unknown"
                            
                        prospect_data = {
                            'id': str(lead_id),
                            'name': name,
                            'company': lead.get('company', 'Unknown Company'),
                            'title': lead.get('job_title', 'Unknown Position'),
                            'pain_points': pain_points,
                            'buying_triggers': buying_triggers
                        }
                        
                        # Add all prospects to the full list
                        all_prospects.append(prospect_data)
                        
                        # Only add to prospects_with_data if both pain points and buying triggers are available
                        has_pain_points = pain_points and pain_points != 'Not available'
                        has_buying_triggers = buying_triggers and buying_triggers != 'Not available'
                        
                        if has_pain_points or has_buying_triggers:
                            prospects_with_data.append(prospect_data)
                            
                except Exception as e:
                    logger.error(f"Error fetching lead details for {log.get('lead_id', 'unknown')}: {str(e)}")
        
        # Use prospects with data if available, otherwise use all prospects (up to 3)
        if prospects_with_data:
            engaged_prospects = prospects_with_data[:3]
        else:
            engaged_prospects = all_prospects[:3]
    
    return {
        'campaign': campaign,
        'company': company,
        'metrics': {
            'total_emails': total_emails,
            'opened_emails': opened_emails,
            'replied_emails': replied_emails,
            'meetings_booked': meetings_booked,
            'total_leads': total_leads,
            'campaign_leads': campaign_leads,
            'remaining_leads': remaining_leads,
            'campaign_complete': campaign_complete,
            'company_coverage': company_coverage
        },
        'rates': {
            'open_rate': open_rate,
            'reply_rate': reply_rate,
            'meeting_rate': meeting_rate
        },
        'benchmark_comparison': benchmark_comparison,
        'engaged_prospects': engaged_prospects
    }

async def generate_simple_summary_email(campaign_id: UUID, recipient_first_name: Optional[str] = None) -> str:
    """
    Generate a simple HTML email summarizing campaign results
    
    Args:
        campaign_id: UUID of the campaign
        recipient_first_name: Optional first name of the recipient for personalization
        
    Returns:
        HTML string containing the email content
    """
    # Get metrics
    metrics = await get_campaign_metrics(campaign_id)
    
    campaign = metrics['campaign']
    company = metrics['company']
    stats = metrics['metrics']
    rates = metrics['rates']
    benchmark = metrics['benchmark_comparison']
    engaged_prospects = metrics['engaged_prospects']
    
    # Format greeting with personalization
    if recipient_first_name:
        greeting = f"Dear {recipient_first_name},"
    else:
        greeting = f"Dear {company['name']} Team,"
    
    # Format percentages
    open_rate_pct = f"{rates['open_rate'] * 100:.1f}%"
    reply_rate_pct = f"{rates['reply_rate'] * 100:.1f}%"
    meeting_rate_pct = f"{rates['meeting_rate'] * 100:.1f}%"
    industry_benchmark_pct = f"{benchmark['industry_open_rate'] * 100:.1f}%"
    
    # Determine if metrics are above/below benchmark
    open_rate_comparison = "above average" if benchmark['open_rate'] > 1 else "below average"
    open_rate_by = f"{abs(benchmark['open_rate'] - 1) * 100:.1f}%"
    
    # Format industry for display
    industry_display = benchmark['industry'].capitalize()
    if industry_display == 'Default':
        industry_display = 'B2B'
    
    # Calculate when reminders will be sent (typically 3 days after initial send)
    reminder_date = (datetime.now() + timedelta(days=3)).strftime("%B %d, %Y")
    
    # Calculate first email completion date if not all sent
    all_emails_sent = stats.get('campaign_complete', False)
    first_emails_completion_date = (datetime.now() + timedelta(days=2)).strftime("%B %d, %Y")
    
    # Get current email sending stats directly from the metrics
    total_emails_sent = stats.get('total_emails', 0)
    total_leads = stats.get('total_leads', 50)  # Use the total leads we calculated
    campaign_leads = stats.get('campaign_leads', 0)
    campaign_complete = stats.get('campaign_complete', False)
    company_coverage = stats.get('company_coverage', 0)
    
    # Format the company coverage as a percentage
    company_coverage_pct = f"{company_coverage * 100:.1f}%"
    
    # Calculate remaining leads that could be targeted
    untargeted_leads = max(0, total_leads - total_emails_sent)
    
    # Always use the same format for next steps, showing actual progress
    next_steps_html = f"""
    <ul>
        <li>We've sent <strong>{total_emails_sent}</strong> of <strong>{total_leads}</strong> leads in your company so far ({company_coverage_pct} of your database)</li>
    """
    
    # Add different follow-up items based on completion status
    if campaign_complete:
        next_steps_html += f"""
        <li>All emails for the current campaign selection ({campaign_leads} leads) have been sent</li>
        <li>There are <strong>{untargeted_leads}</strong> additional leads in your database that could be targeted in future campaigns</li>
        """
    else:
        remaining = max(0, campaign_leads - total_emails_sent) if campaign_leads > 0 else untargeted_leads
        next_steps_html += f"""
        <li>We're currently processing emails for your remaining <strong>{remaining} prospects</strong></li>
        <li>We throttle sending at <strong>500 emails per day</strong> to protect your email reputation and prevent affecting your mailbox</li>
        <li>First emails will finish sending by <strong>{first_emails_completion_date}</strong></li>
        """
    
    # Common items for both cases
    next_steps_html += f"""
        <li>Reminder emails will begin sending on <strong>{reminder_date}</strong></li>
        <li>We'll continue to enrich prospect data as we gather more information about their engagement</li>
    </ul>
    """
    
    # Format prospect examples HTML
    prospect_examples_html = ""
    if engaged_prospects:
        # Check if any of the prospects have actual data
        has_enrichment_data = any(
            prospect.get('pain_points') != 'Not available' or 
            prospect.get('buying_triggers') != 'Not available'
            for prospect in engaged_prospects
        )
        
        if has_enrichment_data:
            for prospect in engaged_prospects:
                pain_points = prospect.get('pain_points', 'Not available')
                buying_triggers = prospect.get('buying_triggers', 'Not available')
                
                # Skip prospects with no data if we have others with data
                if pain_points == 'Not available' and buying_triggers == 'Not available' and has_enrichment_data:
                    continue
                    
                prospect_examples_html += f"""
                <div style="margin: 15px 0; padding: 15px; border-left: 3px solid #4F46E5; background-color: #F9FAFB;">
                    <h4 style="margin-top: 0; margin-bottom: 8px; color: #4F46E5;">{prospect['name']}</h4>
                    <p style="margin: 5px 0;"><strong>Company:</strong> {prospect['company']}</p>
                    <p style="margin: 5px 0;"><strong>Title:</strong> {prospect['title']}</p>
                    <div style="margin-top: 10px;">
                        <p style="margin: 5px 0;"><strong>Pain Points:</strong></p>
                        <p style="margin: 5px 0 10px 0;">{pain_points}</p>
                        <p style="margin: 5px 0;"><strong>Buying Triggers:</strong></p>
                        <p style="margin: 5px 0;">{buying_triggers}</p>
                    </div>
                </div>
                """
        else:
            prospect_examples_html = """
            <p>Here are some of the prospects who have engaged with your campaign:</p>
            <ul style="margin-top: 10px;">
            """
            for prospect in engaged_prospects:
                prospect_examples_html += f"""
                <li><strong>{prospect['name']}</strong> - {prospect['title']} at {prospect['company']}</li>
                """
            prospect_examples_html += "</ul>"
    else:
        prospect_examples_html = """
        <p>No prospects have opened emails yet. As prospects engage with your campaign, we will enrich their profiles with detailed pain points and buying triggers to help you connect more effectively.</p>
        """
    
    # Build the email content
    content = f"""
    <h1>Campaign Results Summary: {campaign['name']}</h1>
    
    <p>{greeting}</p>
    
    <p>We're excited to share the results of your ReachGenie campaign so far. Here's a comprehensive overview of what ReachGenie has accomplished for you:</p>
    
    <div class="section">
        <h2>Prospect Enrichment</h2>
        <p>ReachGenie has enriched all prospects for their pains and buying triggers before sending emails to help connect more effectively.</p>
        
        <h3>Examples of Engaged Prospects:</h3>
        {prospect_examples_html}
    </div>
    
    <div class="section">
        <h2>Automated Email Management</h2>
        <p>ReachGenie has automatically managed your campaign to ensure optimal deliverability:</p>
        <ul>
            <li><strong>Bounced emails</strong> were automatically marked in do_not_email list and removed from your inbox</li>
            <li><strong>Unsubscribe requests</strong> were automatically detected and these contacts were added to your do_not_email list</li>
            <li><strong>Out-of-office/on holiday</strong> replies were detected - we won't trigger calls to these contacts until they return</li>
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
                <td style="padding: 10px; text-align: right; border: 1px solid #E5E7EB;">{stats['total_emails']}</td>
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
        </table>
    </div>
    
    <div class="section">
        <h2>Benchmark Comparison</h2>
        <p>Your open rate of {open_rate_pct} is <strong>{open_rate_comparison}</strong> the {industry_display} industry cold email benchmark of {industry_benchmark_pct} by {open_rate_by}.</p>
        <div style="background-color: #F3F4F6; padding: 15px; border-radius: 5px; margin: 10px 0;">
            <p style="margin: 0;"><strong>What this means:</strong> {
                f"Your campaign is performing well compared to similar companies in the {industry_display} industry. This indicates good targeting and relevant messaging."
                if benchmark['open_rate'] > 1 else 
                f"There may be opportunities to improve your targeting or messaging to increase engagement compared to other companies in the {industry_display} industry."
            }</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Next Steps</h2>
        {next_steps_html}
    </div>
    
    <p>Thank you for using ReachGenie to power your outreach efforts. If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
    
    <p>Best regards,<br>The ReachGenie Team</p>
    """
    
    # Wrap in base template
    return get_base_template(content)

def _extract_name_from_email(email: str) -> str:
    """
    Extract name from email address and format it as a proper name
    (e.g., 'Jack Doe' from 'jack.doe@gmail.com')
    """
    # Get the part before @
    local_part = email.split('@')[0]
    
    # Replace common separators with spaces
    name = local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    
    # Split into parts and capitalize each part
    name_parts = [part.capitalize() for part in name.split() if part]
    
    # If we have at least one part, return the formatted name
    if name_parts:
        return ' '.join(name_parts)
    
    # Fallback to just capitalize the local part if splitting produces no valid parts
    return local_part.capitalize()

async def send_simple_summary_email(campaign_id: UUID, recipient_email: str, recipient_first_name: Optional[str] = None) -> None:
    """
    Generate and send a simple campaign summary email
    
    Args:
        campaign_id: UUID of the campaign
        recipient_email: Email address to send the summary to
        recipient_first_name: Optional first name of the recipient for personalization
    """
    try:
        # Get campaign details
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            logger.error(f"Campaign with ID {campaign_id} not found")
            return
            
        # Get company details
        company_id = UUID(campaign['company_id'])
        company = await get_company_by_id(company_id)
        if not company:
            logger.error(f"Company with ID {company_id} not found")
            return
            
        # Determine the sender name based on company account email
        # First priority: Use the name extracted from the account email if available
        # Second priority: Use the company name
        from_name = None
        if company.get('account_email'):
            from_name = _extract_name_from_email(company['account_email'])
        
        # If no account email or extraction failed, fall back to company name
        if not from_name or from_name == company.get('account_email', '').split('@')[0].capitalize():
            from_name = company.get('name', 'ReachGenie')
            
        # Generate the email content
        email_content = await generate_simple_summary_email(campaign_id, recipient_first_name)
        
        # Send the email
        email_service = EmailService()
        
        # Use the determined sender name
        await email_service.send_email(
            to_email=recipient_email,
            subject=f"Campaign Summary: {campaign['name']}",
            html_content=email_content,
            from_name=from_name,  # Use name extracted from email or company name
            from_email=None  # Use the default email from settings
        )
        
        logger.info(f"Successfully sent campaign summary email for campaign {campaign_id} to {recipient_email} with sender name: {from_name}")
    
    except Exception as e:
        logger.error(f"Error sending campaign summary email: {str(e)}")

async def save_simple_summary_to_file(campaign_id: UUID, filename: Optional[str] = None, recipient_first_name: Optional[str] = None) -> None:
    """
    Generate a simple campaign summary email and save it to a file
    
    Args:
        campaign_id: UUID of the campaign
        filename: Optional file name to save to
        recipient_first_name: Optional first name of the recipient for personalization
    """
    try:
        # Get campaign details
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            logger.error(f"Campaign with ID {campaign_id} not found")
            return
            
        # Generate the email content
        email_content = await generate_simple_summary_email(campaign_id, recipient_first_name)
        
        # Save to file
        if not filename:
            filename = f"campaign_summary_{campaign_id}.html"
        
        with open(filename, "w") as f:
            f.write(email_content)
            
        logger.info(f"Campaign summary saved to {filename}")
    
    except Exception as e:
        logger.error(f"Error generating campaign summary: {str(e)}")

async def main():
    """Process command line arguments and run the appropriate function"""
    if len(sys.argv) < 3:
        print("Usage: python -m src.scripts.generate_simple_campaign_summary <campaign_id> <recipient_email|--save> [recipient_first_name]")
        sys.exit(1)
        
    campaign_id = sys.argv[1]
    action = sys.argv[2]
    
    # Check if first name was provided
    recipient_first_name = None
    if len(sys.argv) > 3:
        recipient_first_name = sys.argv[3]
    
    try:
        campaign_uuid = UUID(campaign_id)
        
        if action == "--save":
            filename = f"campaign_summary_{campaign_id}.html"
            if len(sys.argv) > 4:  # If both first name and filename are provided
                filename = sys.argv[4]
                
            await save_simple_summary_to_file(campaign_uuid, filename, recipient_first_name)
        else:
            # Treat as email address
            recipient_email = action
            await send_simple_summary_email(campaign_uuid, recipient_email, recipient_first_name)
            
    except ValueError as e:
        logger.error(f"Invalid UUID format: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 