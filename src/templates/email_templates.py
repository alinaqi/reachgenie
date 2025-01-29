"""
Email templates for system-wide use.
Each template is a function that returns HTML content with required parameters.
"""

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