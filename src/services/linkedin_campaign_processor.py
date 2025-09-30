"""
LinkedIn campaign processor for handling LinkedIn messaging campaigns
"""
import asyncio
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime
import logging
from src.database import get_pg_pool
from src.services.linkedin_service import linkedin_service
from src.services.perplexity_service import perplexity_service
from src.ai_services.message_generation import MessageGenerationService
import json

logger = logging.getLogger(__name__)

class LinkedInCampaignProcessor:
    """Process LinkedIn messaging campaigns"""
    
    def __init__(self):
        self.message_service = MessageGenerationService()
    
    async def process_campaign_run(
        self,
        campaign_run_id: UUID,
        campaign: Dict[str, Any],
        company: Dict[str, Any],
        leads: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a LinkedIn campaign run.
        
        Args:
            campaign_run_id: The campaign run ID
            campaign: Campaign details
            company: Company details
            leads: List of leads to process
            
        Returns:
            Processing results
        """
        results = {
            "total": len(leads),
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        # Get LinkedIn connection for the company
        linkedin_connection = await self._get_company_linkedin_connection(company['id'])
        if not linkedin_connection:
            error = "No LinkedIn account connected for this company"
            logger.error(error)
            results["errors"].append(error)
            return results
        
        # Check if account is OK
        if linkedin_connection['account_status'] != 'OK':
            error = f"LinkedIn account status is {linkedin_connection['account_status']}"
            logger.error(error)
            results["errors"].append(error)
            return results
        
        # Process each lead
        for lead in leads:
            try:
                # Skip if no LinkedIn ID
                if not lead.get('personal_linkedin_id'):
                    logger.info(f"Skipping lead {lead['name']} - no LinkedIn ID")
                    results["skipped"] += 1
                    continue
                
                # Check if already messaged
                existing = await self._check_existing_message(
                    lead['id'],
                    campaign['id'],
                    linkedin_connection['id']
                )
                if existing:
                    logger.info(f"Skipping lead {lead['name']} - already messaged")
                    results["skipped"] += 1
                    continue
                
                # Generate personalized message
                message = await self._generate_personalized_message(
                    lead, campaign, company
                )
                
                # Check if we need to send invitation first
                if lead.get('linkedin_network_distance') not in ['FIRST_DEGREE', 'DISTANCE_1']:
                    # Send invitation
                    if campaign.get('linkedin_invitation_template'):
                        invitation_message = await self._generate_invitation_message(
                            lead, campaign, company
                        )
                        await self._send_invitation(
                            linkedin_connection['unipile_account_id'],
                            lead['personal_linkedin_id'],
                            invitation_message,
                            campaign_run_id,
                            campaign['id'],
                            lead['id']
                        )
                        results["sent"] += 1
                    else:
                        logger.info(f"Skipping lead {lead['name']} - not connected and no invitation template")
                        results["skipped"] += 1
                    continue
                
                # Send message
                await self._send_message(
                    linkedin_connection['unipile_account_id'],
                    lead['personal_linkedin_id'],
                    message,
                    campaign.get('linkedin_inmail_enabled', False),
                    campaign_run_id,
                    campaign['id'],
                    lead['id'],
                    linkedin_connection['id']
                )
                
                results["sent"] += 1
                
                # Delay between messages
                await asyncio.sleep(20)  # Configurable delay
                
            except Exception as e:
                logger.error(f"Failed to process lead {lead.get('name', 'Unknown')}: {str(e)}")
                results["failed"] += 1
                results["errors"].append(f"{lead.get('name', 'Unknown')}: {str(e)}")
        
        return results
    
    async def _get_company_linkedin_connection(self, company_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the primary LinkedIn connection for a company"""
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow("""
                SELECT lc.*
                FROM linkedin_connections lc
                JOIN companies c ON c.primary_linkedin_connection_id = lc.id
                WHERE c.id = $1
            """, company_id)
    
    async def _check_existing_message(
        self,
        lead_id: UUID,
        campaign_id: UUID,
        linkedin_connection_id: UUID
    ) -> bool:
        """Check if we already sent a message to this lead in this campaign"""
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM linkedin_campaign_logs
                    WHERE lead_id = $1 
                    AND campaign_id = $2
                    AND linkedin_connection_id = $3
                    AND sent_at IS NOT NULL
                )
            """, lead_id, campaign_id, linkedin_connection_id)
            return result
    
    async def _generate_personalized_message(
        self,
        lead: Dict[str, Any],
        campaign: Dict[str, Any],
        company: Dict[str, Any]
    ) -> str:
        """Generate personalized LinkedIn message using AI"""
        template = campaign.get('linkedin_message_template', campaign.get('template', ''))
        
        # Get company insights if available
        insights = None
        if lead.get('company'):
            insights = await perplexity_service.get_company_insights(lead['company'])
        
        # Use message generation service
        message = await self.message_service.generate_linkedin_message(
            template=template,
            lead_data=lead,
            company_data=company,
            insights=insights
        )
        
        return message
    
    async def _generate_invitation_message(
        self,
        lead: Dict[str, Any],
        campaign: Dict[str, Any],
        company: Dict[str, Any]
    ) -> str:
        """Generate personalized LinkedIn invitation message"""
        template = campaign.get('linkedin_invitation_template', '')
        
        # LinkedIn invitations have 300 character limit
        message = await self.message_service.generate_linkedin_invitation(
            template=template,
            lead_data=lead,
            company_data=company,
            max_length=300
        )
        
        return message
    
    async def _send_invitation(
        self,
        account_id: str,
        provider_id: str,
        message: str,
        campaign_run_id: UUID,
        campaign_id: UUID,
        lead_id: UUID
    ):
        """Send LinkedIn invitation and log it"""
        try:
            result = await linkedin_service.send_invitation(
                account_id=account_id,
                provider_id=provider_id,
                message=message
            )
            
            # Log the invitation
            pool = await get_pg_pool()
        async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO linkedin_campaign_logs (
                        campaign_id, campaign_run_id, lead_id,
                        linkedin_connection_id, sent_at
                    )
                    SELECT $1, $2, $3, lc.id, $4
                    FROM linkedin_connections lc
                    WHERE lc.unipile_account_id = $5
                """, campaign_id, campaign_run_id, lead_id, 
                    datetime.utcnow(), account_id)
            
            logger.info(f"Sent invitation to lead {lead_id}")
            
        except Exception as e:
            logger.error(f"Failed to send invitation: {str(e)}")
            raise
    
    async def _send_message(
        self,
        account_id: str,
        provider_id: str,
        message: str,
        use_inmail: bool,
        campaign_run_id: UUID,
        campaign_id: UUID,
        lead_id: UUID,
        linkedin_connection_id: UUID
    ):
        """Send LinkedIn message and log it"""
        try:
            # First check if we have an existing chat
            chat_id = None
            pool = await get_pg_pool()
        async with pool.acquire() as conn:
                existing_chat = await conn.fetchrow("""
                    SELECT lc.unipile_chat_id
                    FROM linkedin_messages lm
                    JOIN linkedin_chats lc ON lm.chat_id = lc.id
                    WHERE lm.lead_id = $1
                    ORDER BY lm.created_at DESC
                    LIMIT 1
                """, lead_id)
                
                if existing_chat:
                    chat_id = existing_chat['unipile_chat_id']
            
            # Send message
            result = await linkedin_service.send_message(
                account_id=account_id,
                chat_id=chat_id,
                attendee_id=provider_id if not chat_id else None,
                text=message,
                inmail=use_inmail
            )
            
            # Extract chat and message info from result
            unipile_chat_id = result.get('chat', {}).get('id') or result.get('id')
            unipile_message_id = result.get('message', {}).get('id')
            
            # Store chat and message in database
            pool = await get_pg_pool()
        async with pool.acquire() as conn:
                # Create or update chat
                chat_id_db = await conn.fetchval("""
                    INSERT INTO linkedin_chats (
                        unipile_chat_id, linkedin_connection_id,
                        last_message_at
                    ) VALUES ($1, $2, $3)
                    ON CONFLICT (unipile_chat_id) 
                    DO UPDATE SET 
                        last_message_at = $3,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, unipile_chat_id, linkedin_connection_id, datetime.utcnow())
                
                # Store message
                await conn.execute("""
                    INSERT INTO linkedin_messages (
                        unipile_message_id, chat_id, campaign_id,
                        campaign_run_id, lead_id, message_text,
                        is_sender, sent_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, unipile_message_id, chat_id_db, campaign_id,
                    campaign_run_id, lead_id, message, True,
                    datetime.utcnow())
                
                # Create campaign log
                await conn.execute("""
                    INSERT INTO linkedin_campaign_logs (
                        campaign_id, campaign_run_id, lead_id,
                        linkedin_connection_id, chat_id, sent_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, campaign_id, campaign_run_id, lead_id,
                    linkedin_connection_id, chat_id_db, datetime.utcnow())
            
            logger.info(f"Sent message to lead {lead_id} in chat {unipile_chat_id}")
            
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            raise

# Create singleton instance
linkedin_campaign_processor = LinkedInCampaignProcessor()
