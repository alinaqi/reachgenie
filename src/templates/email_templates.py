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
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333333;
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
            .content {{
                background-color: #ffffff;
                padding: 30px;
                border-radius: 0 0 5px 5px;
                border: 1px solid #e0e0e0;
            }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #4F46E5;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                color: #666666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {content}
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
            <p style="word-break: break-all;">{reset_link}</p>
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message, please do not reply to this email.</p>
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
            <h1>Welcome to Our Platform!</h1>
        </div>
        <div class="content">
            <p>Hello {user_name},</p>
            <p>Welcome to our platform! We're excited to have you on board.</p>
            <p>If you have any questions or need assistance, don't hesitate to reach out to our support team.</p>
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message, please do not reply to this email.</p>
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
            <p style="word-break: break-all;">{verification_link}</p>
            <p>Best regards,<br>ReachGenie Support Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message, please do not reply to this email.</p>
        </div>
    """
    return get_base_template(content) 