from aiosmtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException, status
import logging
from typing import Optional
from uuid import UUID
import aiosmtplib
import imaplib

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMTPClient:
    # SMTP server configurations for different providers
    SMTP_CONFIGS = {
        "gmail": {
            "server": "smtp.gmail.com",
            "port": 465,  # Using SSL port instead of STARTTLS
            "use_tls": True
        },
        "outlook": {
            "server": "smtp.office365.com",
            "port": 465,
            "use_tls": True
        },
        "yahoo": {
            "server": "smtp.mail.yahoo.com",
            "port": 465,
            "use_tls": True
        }
        # Add more providers as needed
    }

    # IMAP server configurations
    IMAP_CONFIGS = {
        'gmail': 'imap.gmail.com',
        'outlook': 'outlook.office365.com',
        'yahoo': 'imap.mail.yahoo.com'
    }

    def __init__(self, account_email: str, account_password: str, provider: str):
        """
        Initialize SMTP client with email credentials and provider
        
        Args:
            account_email: Email address to send from
            account_password: Password for the email account
            provider: Email provider (e.g., 'gmail', 'outlook', 'yahoo')
        """
        self.email = account_email
        self.password = account_password
        
        # Get provider config or raise error if provider not supported
        provider = provider.lower()
        if provider not in self.SMTP_CONFIGS:
            raise ValueError(
                f"Email provider '{provider}' not supported. "
                f"Supported providers: {', '.join(self.SMTP_CONFIGS.keys())}"
            )
        
        config = self.SMTP_CONFIGS[provider]
        self.smtp_server = config["server"]
        self.smtp_port = config["port"]
        self.use_tls = config["use_tls"]
        
        # Initialize SMTP client
        self.smtp = None

    @staticmethod
    async def test_connections(account_email: str, account_password: str, provider: str) -> None:
        """
        Test both SMTP and IMAP connections
        
        Args:
            account_email: Email address to test
            account_password: Password for the email account
            provider: Email provider (e.g., 'gmail', 'outlook', 'yahoo')
            
        Raises:
            HTTPException: If either connection fails
        """
        # Test SMTP connection
        async with SMTPClient(account_email, account_password, provider) as smtp_client:
            pass  # Context manager will test SMTP connection
        
        # Test IMAP connection
        provider = provider.lower()
        if provider not in SMTPClient.IMAP_CONFIGS:
            raise ValueError(
                f"Email provider '{provider}' not supported for IMAP. "
                f"Supported providers: {', '.join(SMTPClient.IMAP_CONFIGS.keys())}"
            )
        
        try:
            imap = imaplib.IMAP4_SSL(SMTPClient.IMAP_CONFIGS[provider])
            imap.login(account_email, account_password)
            imap.select("INBOX")  # Test inbox access
            imap.logout()
        except imaplib.IMAP4.error as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"IMAP authentication failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to IMAP server: {str(e)}"
            )

    async def connect(self) -> None:
        """
        Establish connection to SMTP server
        """
        try:
            # Initialize with SSL/TLS enabled
            self.smtp = SMTP(
                hostname=self.smtp_server,
                port=self.smtp_port,
                use_tls=self.use_tls,  # Use TLS from the start
                tls_context=None,  # Let it use default SSL context
                timeout=30
            )
            
            # Connect and authenticate
            await self.smtp.connect()
            try:
                await self.smtp.login(self.email, self.password)
            except aiosmtplib.errors.SMTPAuthenticationError as auth_error:
                if "BadCredentials" in str(auth_error) and self.smtp_server == "smtp.gmail.com":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=(
                            "Gmail login failed. If you're using 2-factor authentication, you need to:"
                            "\n1. Go to your Google Account settings"
                            "\n2. Enable 2-Step Verification if not already enabled"
                            "\n3. Generate an App Password (Security → App Passwords)"
                            "\n4. Use that App Password instead of your regular password"
                            "\nFor more details: https://support.google.com/accounts/answer/185833"
                        )
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Authentication failed: {str(auth_error)}"
                    )
            
            logger.info(f"Successfully connected to SMTP server: {self.smtp_server}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            if self.smtp:
                try:
                    await self.smtp.quit()
                except:
                    pass
                self.smtp = None
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to email server: {str(e)}"
            )

    async def disconnect(self) -> None:
        """
        Close SMTP connection
        """
        if self.smtp:
            try:
                await self.smtp.quit()
            except Exception as e:
                logger.error(f"Error disconnecting from SMTP server: {str(e)}")
            finally:
                self.smtp = None

    @staticmethod
    def _extract_name_from_email(email: str) -> str:
        """Extract name from email address (e.g., 'jack.doe' from 'jack.doe@gmail.com')"""
        return email.split('@')[0]

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_name: Optional[str] = None,
        email_log_id: Optional[UUID] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> None:
        """
        Send an email using the configured SMTP connection
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            from_name: Optional sender name to display
            email_log_id: Optional UUID to be used in reply-to address
            in_reply_to: Optional Message-ID to reference in In-Reply-To header
            references: Optional References header value for threading
        """
        if not self.smtp or not self.smtp.is_connected:
            await self.connect()
            
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            # Use provided from_name or extract from email
            display_name = self._extract_name_from_email(self.email)
            message["From"] = f"{display_name} <{self.email}>"
            message["To"] = to_email
            
            # Add Reply-To header if email_log_id is provided
            if email_log_id:
                # Split email into local part and domain
                local_part, domain = self.email.split('@')
                # Convert UUID to string for the email address
                email_log_id_str = str(email_log_id) if isinstance(email_log_id, UUID) else email_log_id
                reply_to = f"{local_part}+{email_log_id_str}@{domain}"
                message["Reply-To"] = reply_to
            
            # Add In-Reply-To header if provided
            if in_reply_to:
                message["In-Reply-To"] = in_reply_to
                
            # Add References header if provided
            if references:
                message["References"] = references
            
            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            await self.smtp.send_message(message)
            logger.info(f"Successfully sent email to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {str(e)}"
            )
        
    async def __aenter__(self):
        """
        Async context manager entry
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit
        """
        await self.disconnect() 