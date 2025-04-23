"""
Email templates for system-wide use.
Each template is a function that returns HTML content with required parameters.
"""

from typing import List, Dict

def get_base_template(content: str) -> str:
    """
    Base template that wraps content with common styling and structure.
    
    Args:
        content: The main content to be wrapped in the base template
        
    Returns:
        str: Complete HTML template with the content wrapped in common styling
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
                line-height: 1.6;
                color: #333333;
                font-size: 16px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #4F46E5;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .header h1 {{
                font-size: 24px;
                margin: 0;
                font-weight: 600;
            }}
            .content {{
                background-color: #ffffff;
                padding: 30px;
                border-radius: 0 0 5px 5px;
                border: 1px solid #e0e0e0;
            }}
            .content p {{
                font-size: 16px;
                margin: 16px 0;
            }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #4F46E5;
                color: white !important;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                font-family: inherit;
                font-size: 16px;
                font-weight: 500;
            }}
            .button:visited {{
                color: white !important;
            }}
            .button:hover {{
                background-color: #4338CA;
                color: white !important;
            }}
            .button:link {{
                color: white !important;
            }}
            .button:active {{
                color: white !important;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                color: #666666;
                font-size: 14px;
            }}
            .footer p {{
                margin: 8px 0;
            }}
            .link-text {{
                color: #6B7280;
                font-size: 14px;
                word-break: break-all;
            }}
            .section {{
                margin: 30px 0;
                padding: 15px;
                border-left: 4px solid #4F46E5;
                background-color: #F5F7FF;
            }}
            .section h2 {{
                color: #4F46E5;
                font-size: 18px;
                margin-top: 0;
                margin-bottom: 15px;
            }}
            .tips-section {{
                margin: 30px 0;
                padding: 15px;
                background-color: #F9FAFB;
                border-left: 4px solid #3B82F6;
            }}
            .tips-section h2 {{
                color: #2563EB;
                font-size: 18px;
                margin-top: 0;
                margin-bottom: 15px;
            }}
            .tip {{
                margin-bottom: 20px;
            }}
            .tip h3 {{
                color: #1D4ED8;
                font-size: 16px;
                margin-bottom: 5px;
            }}
            .tip p {{
                margin-top: 5px;
                padding-left: 10px;
                border-left: 2px solid #DBEAFE;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {content}
            
            <div class="footer">
                <p>This is an automated message, please do not reply to this email.</p>
                <p style="margin-top: 10px; font-size: 12px;">
                    ReachGenie - AI-Powered Sales Outreach
                </p>
            </div>
        </div>
    </body>
    </html>
    """

def get_password_reset_template(reset_link: str) -> str:
    """
    Password reset email template.
    
    Args:
        reset_link: The password reset link to be included in the email
        
    Returns:
        str: Complete HTML template for password reset email
    """
    content = f"""
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>We received a request to reset your password. If you didn't make this request, you can safely ignore this email.</p>
            <p>To reset your password, click the button below:</p>
            <p style="text-align: center;">
                <a href="{reset_link}" class="button">Reset Password</a>
            </p>
            <p>This link will expire in 1 hour for security reasons.</p>
            <p>If you're having trouble clicking the button, copy and paste this URL into your browser:</p>
            <p class="link-text">{reset_link}</p>
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
    """
    return get_base_template(content)

def get_welcome_template(user_name: str) -> str:
    """
    Welcome email template for new users.
    
    Args:
        user_name: The name of the user to welcome
        
    Returns:
        str: Complete HTML template for welcome email
    """
    content = f"""
        <div class="header">
            <h1>Welcome to ReachGenie!</h1>
        </div>
        <div class="content">
            <p>Hello {user_name},</p>
            <p>Welcome to ReachGenie! We're excited to have you on board. Our AI-powered platform is designed to streamline your outbound sales process and help you connect with potential customers more effectively.</p>
            
            <p>Here's what you can do to get started:</p>
            <ol style="margin-left: 20px; line-height: 1.8;">
                <li><strong>Create Your Company Profile:</strong> Set up your company details to personalize your outreach.</li>
                <li><strong>Configure Email Settings:</strong> Connect your email account to enable automated email campaigns.</li>
                <li><strong>Import Your Leads:</strong> Upload your lead list or add leads individually to start engaging with prospects.</li>
                <li><strong>Set Up Email Campaigns:</strong> Create personalized email campaigns with our AI-powered templates.</li>
                <li><strong>Connect Your Calendar:</strong> Integrate your calendar to streamline meeting scheduling with leads.</li>
            </ol>
            
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
    """
    return get_base_template(content)

def get_account_verification_template(verification_link: str) -> str:
    """
    Account verification email template.
    
    Args:
        verification_link: The verification link to be included in the email
        
    Returns:
        str: Complete HTML template for account verification email
    """
    content = f"""
        <div class="header">
            <h1>Verify Your Account</h1>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>Thank you for creating an account. Please verify your email address by clicking the button below:</p>
            <p style="text-align: center;">
                <a href="{verification_link}" class="button">Verify Email</a>
            </p>
            <p>If you're having trouble clicking the button, copy and paste this URL into your browser:</p>
            <p class="link-text">{verification_link}</p>
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
    """
    return get_base_template(content)

def get_invite_template(
    company_name: str, 
    invite_link: str, 
    inviter_name: str, 
    recipient_name: str = "",
    value_proposition: str = "",
    engagement_tips: list = None
) -> str:
    """
    Company invite email template with personalization.
    
    Args:
        company_name: Name of the company sending the invite
        invite_link: The invite link with token
        inviter_name: Name of the person who sent the invite
        recipient_name: Optional name of the recipient for personalization
        value_proposition: Optional personalized value proposition
        engagement_tips: Optional list of engagement tips
        
    Returns:
        str: Complete HTML template for company invite email
    """
    # Extract first name if the full name is provided
    first_name = recipient_name.split()[0] if recipient_name else ""
    greeting = f"Hello {first_name}," if first_name else "Hello,"
    
    # Start with the basic content
    content = f"""
        <div class="header">
            <h1>You've Been Invited to Join "{company_name}"</h1>
        </div>
        <div class="content">
            <p>{greeting}</p>
            <p>{inviter_name} has invited you to join "{company_name}" on ReachGenie. Click the button below to accept the invitation and set up your account:</p>
            <p style="text-align: center;">
                <a href="{invite_link}" class="button" style="color: white !important;">Accept Invitation</a>
            </p>
    """
    
    # Add value proposition if provided
    if value_proposition:
        # Check if value proposition starts with "Hi there" or similar and replace it
        modified_value_proposition = value_proposition
        if first_name and value_proposition:
            # Replace common greetings with the first name followed by exclamation
            modified_value_proposition = value_proposition.replace("Hi there!", f"{first_name}!")
            modified_value_proposition = modified_value_proposition.replace("Hello!", f"{first_name}!")
            modified_value_proposition = modified_value_proposition.replace("Hi!", f"{first_name}!")
        
        content += f"""
            <div class="section">
                <h2>How ReachGenie Can Help {company_name}</h2>
                {modified_value_proposition}
            </div>
        """
    
    # Add engagement tips if provided
    if engagement_tips and len(engagement_tips) > 0:
        content += f"""
            <div class="tips-section">
                <h2>Tips for Engaging Your Prospects</h2>
        """
        
        for i, tip in enumerate(engagement_tips):
            title = tip.get("title", f"Tip {i+1}")
            tip_content = tip.get("content", "")
            
            content += f"""
                <div class="tip">
                    <h3>{i+1}. {title}</h3>
                    <p>{tip_content}</p>
                </div>
            """
        
        content += """
            </div>
        """
    
    # Add link fallback and closing
    content += f"""
            <p>If you're having trouble clicking the button, copy and paste this URL into your browser:</p>
            <p class="link-text">{invite_link}</p>
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
    """
    
    return get_base_template(content)

def get_company_addition_template(user_name: str, company_name: str, inviter_name: str) -> str:
    """
    Template for notifying existing users they've been added to a company.
    
    Args:
        user_name: Name of the user being added
        company_name: Name of the company they're being added to
        inviter_name: Name of the person who added them
        
    Returns:
        str: Complete HTML template for company addition notification
    """
    content = f"""
        <div class="header">
            <h1>You've Been Added to "{company_name}"</h1>
        </div>
        <div class="content">
            <p>Hello {user_name},</p>
            <p>{inviter_name} has added you to "{company_name}" on ReachGenie. You can now access the company's dashboard and collaborate with your team members.</p>
            <p>To access your new company workspace, simply log in to your ReachGenie account and select "{company_name}" from your company list.</p>
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
    """
    return get_base_template(content)

def get_email_campaign_stats_template(
    campaign_name: str,
    company_name: str,
    date: str,
    emails_sent: int,
    emails_opened: int,
    emails_replied: int,
    meetings_booked: int,
    engaged_leads: List[Dict[str, str]]
) -> str:
    """
    Campaign statistics email template.
    
    Args:
        campaign_name: Name of the campaign
        company_name: Name of the company
        date: Date for which stats are being shown
        emails_sent: Number of emails sent
        emails_opened: Number of emails opened
        emails_replied: Number of emails replied to
        meetings_booked: Number of meetings booked
        engaged_leads: List of dictionaries containing lead details (name, company, job_title)
        
    Returns:
        str: Complete HTML template for campaign statistics email
    """
    # Calculate percentages (avoid division by zero)
    open_rate = round((emails_opened / emails_sent * 100) if emails_sent > 0 else 0)
    reply_rate = round((emails_replied / emails_sent * 100) if emails_sent > 0 else 0)
    meeting_rate = round((meetings_booked / emails_sent * 100) if emails_sent > 0 else 0)
    
    # Generate engaged leads HTML
    engaged_leads_html = ""
    if engaged_leads:
        engaged_leads_html = """
            <div class="section">
                <h2>Top Engaged Leads</h2>
                <div style="margin-left: 10px;">
        """
        for lead in engaged_leads:
            engaged_leads_html += f"""
                <div style="margin-bottom: 15px;">
                    <strong>{lead['name']}</strong><br>
                    {lead['job_title']} at {lead['company']}
                </div>
            """
        engaged_leads_html += """
                </div>
            </div>
        """

    content = f"""
        <div class="header">
            <h1>Campaign Performance Update</h1>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>Here's your daily performance update for the campaign "<strong>{campaign_name}</strong>" at {company_name} for {date}:</p>
            
            <div class="section">
                <h2>Campaign Statistics</h2>
                <div style="margin-left: 10px;">
                    <p><strong>Emails Sent:</strong> {emails_sent}</p>
                    <p><strong>Emails Opened:</strong> {emails_opened} ({open_rate}% open rate)</p>
                    <p><strong>Emails Replied:</strong> {emails_replied} ({reply_rate}% reply rate)</p>
                    <p><strong>Meetings Booked:</strong> {meetings_booked} ({meeting_rate}% conversion rate)</p>
                </div>
            </div>
            
            {engaged_leads_html}
            
            <p>You can view more detailed statistics and manage your campaign in the ReachGenie dashboard.</p>
            
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
    """
    return get_base_template(content)

def get_call_campaign_stats_template(
    campaign_name: str,
    company_name: str,
    date: str,
    calls_sent: int,
    meetings_booked: int
) -> str:
    """
    Campaign statistics email template for campaign type 'call'.
    
    Args:
        campaign_name: Name of the campaign
        company_name: Name of the company
        date: Date for which stats are being shown
        calls_sent: Number of calls sent
        meetings_booked: Number of meetings booked
        
    Returns:
        str: Complete HTML template for campaign statistics email
    """
    # Calculate percentages (avoid division by zero)
    meeting_rate = round((meetings_booked / calls_sent * 100) if calls_sent > 0 else 0)

    content = f"""
        <div class="header">
            <h1>Campaign Performance Update</h1>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>Here's your daily performance update for the campaign "<strong>{campaign_name}</strong>" at {company_name} for {date}:</p>
            
            <div class="section">
                <h2>Campaign Statistics</h2>
                <div style="margin-left: 10px;">
                    <p><strong>Calls Dispatched:</strong> {calls_sent}</p>
                    <p><strong>Meetings Booked:</strong> {meetings_booked} ({meeting_rate}% conversion rate)</p>
                </div>
            </div>
            
            <p>You can view more detailed statistics and manage your campaign in the ReachGenie dashboard.</p>
            
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
    """
    return get_base_template(content)