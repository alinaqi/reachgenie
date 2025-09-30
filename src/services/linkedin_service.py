"""
LinkedIn service module for handling all LinkedIn-related functionality via Unipile API.
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta, timezone
import logging
from src.config import get_settings
from src.database import get_pg_pool
import json

logger = logging.getLogger(__name__)
settings = get_settings()

def format_unipile_date(dt=None):
    """Format datetime for Unipile API (YYYY-MM-DDTHH:MM:SS.sssZ)"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    # Format with exactly 3 decimal places for milliseconds
    iso_str = dt.isoformat()
    # Extract the datetime part and microseconds
    if '.' in iso_str:
        dt_part = iso_str.split('.')[0]
        microseconds = int(iso_str.split('.')[1][:6].rstrip('+'))
        milliseconds = microseconds // 1000
        return f"{dt_part}.{milliseconds:03d}Z"
    else:
        return f"{iso_str.split('+')[0]}.000Z"

class LinkedInService:
    """Service for managing LinkedIn operations through Unipile API"""
    
    def __init__(self):
        self.api_key = settings.unipile_api_key
        self.base_url = f"https://{settings.unipile_dsn}/api/v1"
        self.headers = {
            'X-API-KEY': self.api_key,
            'accept': 'application/json',
            'content-type': 'application/json'
        }
        # Database connection will be obtained when needed
    
    async def create_hosted_auth_link(
        self, 
        company_id: UUID,
        user_id: UUID,
        success_redirect_url: str,
        failure_redirect_url: str
    ) -> Dict[str, str]:
        """
        Generate a hosted authentication link for LinkedIn account connection.
        
        Returns:
            Dict containing the authentication URL
        """
        notify_url = f"{settings.webhook_base_url}/api/v1/webhooks/unipile/account-connected"
        
        payload = {
            "type": "create",
            "providers": ["LINKEDIN"],
            "api_url": self.base_url,
            "expiresOn": format_unipile_date(datetime.now(timezone.utc) + timedelta(hours=1)),
            "success_redirect_url": success_redirect_url,
            "failure_redirect_url": failure_redirect_url,
            "notify_url": notify_url,
            "name": f"{company_id}:{user_id}"  # Internal identifier
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/hosted/accounts/link",
                headers=self.headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"url": data["url"]}
                else:
                    error_data = await response.text()
                    raise Exception(f"Failed to create auth link: {error_data}")
    
    async def reconnect_account(
        self,
        account_id: str,
        success_redirect_url: str,
        failure_redirect_url: str
    ) -> Dict[str, str]:
        """Reconnect a disconnected LinkedIn account"""
        notify_url = f"{settings.webhook_base_url}/api/v1/webhooks/unipile/account-reconnected"
        
        payload = {
            "type": "reconnect",
            "reconnect_account": account_id,
            "providers": ["LINKEDIN"],
            "api_url": self.base_url,
            "expiresOn": format_unipile_date(datetime.now(timezone.utc) + timedelta(hours=1)),
            "success_redirect_url": success_redirect_url,
            "failure_redirect_url": failure_redirect_url,
            "notify_url": notify_url
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/hosted/accounts/link",
                headers=self.headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"url": data["url"]}
                else:
                    error_data = await response.text()
                    raise Exception(f"Failed to create reconnect link: {error_data}")
    
    async def get_account_info(self, account_id: str) -> Dict[str, Any]:
        """Get LinkedIn account information"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/accounts/{account_id}",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.text()
                    raise Exception(f"Failed to get account info: {error_data}")
    
    async def get_user_profile(
        self, 
        account_id: str, 
        profile_identifier: str,
        use_provider_id: bool = False
    ) -> Dict[str, Any]:
        """
        Get LinkedIn user profile information.
        
        Args:
            account_id: Unipile account ID
            profile_identifier: LinkedIn profile URL slug or provider ID
            use_provider_id: Whether profile_identifier is a provider ID
        
        Returns:
            User profile data
        """
        params = {"account_id": account_id}
        
        # Add sections to get complete profile data
        if not use_provider_id:
            params["linkedin_sections"] = "*"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/users/{profile_identifier}",
                headers=self.headers,
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.text()
                    raise Exception(f"Failed to get user profile: {error_data}")
    
    async def send_invitation(
        self,
        account_id: str,
        provider_id: str,
        message: str
    ) -> Dict[str, Any]:
        """Send LinkedIn connection invitation"""
        # Check daily limits
        invites_today = await self._get_invites_sent_today(account_id)
        if invites_today >= settings.linkedin_daily_invite_limit:
            raise Exception(f"Daily invitation limit reached ({settings.linkedin_daily_invite_limit})")
        
        payload = {
            "provider_id": provider_id,
            "account_id": account_id,
            "message": message[:300]  # LinkedIn limit is 300 characters
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/users/invite",
                headers=self.headers,
                json=payload
            ) as response:
                if response.status == 200:
                    # Log the invitation
                    await self._log_invitation(account_id, provider_id)
                    return await response.json()
                else:
                    error_data = await response.text()
                    raise Exception(f"Failed to send invitation: {error_data}")
    
    async def send_message(
        self,
        account_id: str,
        text: str,
        chat_id: Optional[str] = None,
        attendee_id: Optional[str] = None,
        inmail: bool = False
    ) -> Dict[str, Any]:
        """
        Send a LinkedIn message.
        
        Args:
            account_id: Unipile account ID
            chat_id: Existing chat ID (if replying)
            attendee_id: LinkedIn user provider ID (if starting new chat)
            text: Message text
            inmail: Whether to send as InMail (premium feature)
        
        Returns:
            Message and chat information
        """
        # Rate limiting
        await self._enforce_message_delay()
        
        if chat_id:
            # Send message to existing chat
            url = f"{self.base_url}/chats/{chat_id}/messages"
            payload = {"text": text}
        else:
            # Start new chat
            if not attendee_id:
                raise ValueError("Either chat_id or attendee_id must be provided")
            
            url = f"{self.base_url}/chats"
            payload = {
                "account_id": account_id,
                "text": text,
                "attendees_ids": [attendee_id]
            }
            
            if inmail:
                payload["linkedin"] = {
                    "api": "classic",  # or "sales_navigator" / "recruiter"
                    "inmail": True
                }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self.headers,
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.text()
                    raise Exception(f"Failed to send message: {error_data}")
    
    async def get_chats(
        self,
        account_id: str,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of LinkedIn chats"""
        params = {
            "account_id": account_id,
            "limit": limit
        }
        if cursor:
            params["cursor"] = cursor
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/chats",
                headers=self.headers,
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.text()
                    raise Exception(f"Failed to get chats: {error_data}")
    
    async def get_messages(
        self,
        chat_id: str,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get messages from a specific chat"""
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/chats/{chat_id}/messages",
                headers=self.headers,
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.text()
                    raise Exception(f"Failed to get messages: {error_data}")
    
    async def sync_lead_linkedin_profile(
        self,
        lead_id: UUID,
        account_id: str,
        linkedin_url: Optional[str] = None,
        provider_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync LinkedIn profile data for a lead.
        
        Args:
            lead_id: Lead UUID in our database
            account_id: Unipile account ID
            linkedin_url: LinkedIn profile URL
            provider_id: LinkedIn provider ID
        
        Returns:
            Updated lead data
        """
        if not linkedin_url and not provider_id:
            raise ValueError("Either linkedin_url or provider_id must be provided")
        
        # Extract profile identifier from URL if needed
        profile_identifier = provider_id
        if linkedin_url and not provider_id:
            # Extract from URL like https://www.linkedin.com/in/john-doe
            parts = linkedin_url.rstrip('/').split('/')
            profile_identifier = parts[-1]
        
        try:
            # Get profile data from LinkedIn
            profile_data = await self.get_user_profile(
                account_id, 
                profile_identifier,
                use_provider_id=bool(provider_id)
            )
            
            # Update lead with LinkedIn data
            update_data = {
                "personal_linkedin_id": profile_data.get("provider_id"),
                "linkedin_headline": profile_data.get("headline"),
                "linkedin_network_distance": profile_data.get("network_distance"),
                "linkedin_profile_synced": True,
                "linkedin_last_synced_at": datetime.now(timezone.utc)
            }
            
            # Update enriched data with full profile
            enriched_data = {
                "linkedin_profile": profile_data,
                "synced_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Update in database
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE leads
                    SET 
                        personal_linkedin_id = $1,
                        linkedin_headline = $2,
                        linkedin_network_distance = $3,
                        linkedin_profile_synced = $4,
                        linkedin_last_synced_at = $5,
                        enriched_data = COALESCE(enriched_data, '{}'::jsonb) || $6::jsonb
                    WHERE id = $7
                """, 
                update_data["personal_linkedin_id"],
                update_data["linkedin_headline"],
                update_data["linkedin_network_distance"],
                update_data["linkedin_profile_synced"],
                update_data["linkedin_last_synced_at"],
                json.dumps(enriched_data),
                lead_id
                )
            
            return {
                "lead_id": lead_id,
                "profile_data": profile_data,
                "updated": True
            }
            
        except Exception as e:
            logger.error(f"Failed to sync LinkedIn profile for lead {lead_id}: {str(e)}")
            raise
    
    # Helper methods
    async def _get_invites_sent_today(self, account_id: str) -> int:
        """Get count of invitations sent today"""
        # This would query a table tracking invitations
        # For now, return 0
        return 0
    
    async def _log_invitation(self, account_id: str, provider_id: str):
        """Log an invitation for rate limiting"""
        # This would insert into an invitations tracking table
        pass
    
    async def _enforce_message_delay(self):
        """Enforce delay between messages to avoid rate limiting"""
        await asyncio.sleep(settings.linkedin_message_delay_seconds)
    
    async def send_message_to_profile(
        self,
        account_id: str,
        profile_url: str,
        message: str
    ) -> Dict[str, Any]:
        """Send a message to a LinkedIn profile (creates chat if needed)"""
        try:
            # Get profile data
            profile = await self.get_user_profile(account_id, profile_url)
            provider_id = profile.get("provider_id")
            
            if not provider_id:
                raise Exception("Could not get provider ID for profile")
            
            # Try to send message (will create chat if needed)
            endpoint = f"{self.base_url}/api/v1/chats"
            data = {
                "account_id": account_id,
                "attendees_ids": [provider_id],
                "text": message
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=self.headers,
                    json=data
                ) as response:
                    if response.status in [200, 201]:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        # If not connected, send connection request
                        if "not connected" in error_text.lower():
                            return await self.send_connection_request_simple(
                                account_id, provider_id, message
                            )
                        raise Exception(f"Failed to send message: {error_text}")
                        
        except Exception as e:
            logger.error(f"Failed to send message to {profile_url}: {str(e)}")
            raise
    
    async def send_connection_request_simple(
        self,
        account_id: str,
        provider_id: str,
        message: str
    ) -> Dict[str, Any]:
        """Send a LinkedIn connection request"""
        endpoint = f"{self.base_url}/api/v1/users/invite"
        data = {
            "account_id": account_id,
            "provider_id": provider_id,
            "message": message[:300]  # LinkedIn limit
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                headers=self.headers,
                json=data
            ) as response:
                if response.status in [200, 201]:
                    return {"status": "connection_request_sent"}
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to send connection request: {error_text}")

# Create singleton instance
linkedin_service = LinkedInService()
