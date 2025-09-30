"""
Unipile webhook handlers for LinkedIn events
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Dict, Any
import logging
import json
from src.database import get_pg_pool
from src.auth import get_current_user
from src.config import get_settings
from datetime import datetime
import hmac
import hashlib

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

async def verify_webhook_signature(request: Request, body: bytes) -> bool:
    """Verify webhook signature from Unipile"""
    if not settings.unipile_webhook_secret:
        return True  # Skip verification if no secret configured
    
    signature = request.headers.get("X-Unipile-Signature")
    if not signature:
        return False
    
    expected = hmac.new(
        settings.unipile_webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

@router.post("/api/v1/webhooks/unipile/account-status")
async def handle_account_status_webhook(request: Request):
    """Handle account status updates from Unipile"""
    body = await request.body()
    
    # Verify signature
    if not await verify_webhook_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    data = json.loads(body)
    account_status = data.get("AccountStatus", {})
    
    account_id = account_status.get("account_id")
    status = account_status.get("message")
    account_type = account_status.get("account_type")
    
    if account_type != "LINKEDIN":
        return {"status": "ignored", "reason": "Not a LinkedIn account"}
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Update account status
        await conn.execute("""
            UPDATE linkedin_connections
            SET 
                account_status = $1,
                last_status_update = $2,
                updated_at = $2
            WHERE unipile_account_id = $3
        """, status, datetime.utcnow(), account_id)
        
        # If credentials error, notify the company
        if status == "CREDENTIALS":
            connection = await conn.fetchrow("""
                SELECT lc.*, c.name as company_name, u.email
                FROM linkedin_connections lc
                JOIN companies c ON lc.company_id = c.id
                JOIN users u ON c.user_id = u.id
                WHERE lc.unipile_account_id = $1
            """, account_id)
            
            if connection:
                # TODO: Send email notification about reconnection needed
                logger.warning(f"LinkedIn account {account_id} needs reconnection for company {connection['company_name']}")
    
    return {"status": "success"}

@router.post("/api/v1/webhooks/unipile/account-connected")
async def handle_account_connected_webhook(request: Request):
    """Handle successful account connection from Unipile"""
    body = await request.body()
    
    # Verify signature
    if not await verify_webhook_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    data = json.loads(body)
    
    account_id = data.get("account_id")
    name = data.get("name", "")  # Contains company_id:user_id
    status = data.get("status")
    
    if status != "CREATION_SUCCESS":
        return {"status": "ignored", "reason": f"Unexpected status: {status}"}
    
    # Parse the name to get company_id
    try:
        company_id, user_id = name.split(":")
    except:
        logger.error(f"Invalid name format in webhook: {name}")
        return {"status": "error", "reason": "Invalid name format"}
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Get account info from Unipile
        from src.services.linkedin_service import linkedin_service
        try:
            account_info = await linkedin_service.get_account_info(account_id)
            
            # Create LinkedIn connection record
            connection_id = await conn.fetchval("""
                INSERT INTO linkedin_connections (
                    company_id, unipile_account_id, account_type,
                    account_status, account_feature, account_user_id,
                    display_name, profile_url, connection_email
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """, 
            company_id, account_id, "LINKEDIN",
            "OK", account_info.get("feature"), account_info.get("user_id"),
            account_info.get("display_name"), account_info.get("profile_url"),
            account_info.get("email")
            )
            
            # Update company with primary LinkedIn connection if first one
            await conn.execute("""
                UPDATE companies
                SET primary_linkedin_connection_id = $1
                WHERE id = $2 AND primary_linkedin_connection_id IS NULL
            """, connection_id, company_id)
            
        except Exception as e:
            logger.error(f"Failed to process account connection: {str(e)}")
            return {"status": "error", "reason": str(e)}
    
    return {"status": "success", "connection_id": str(connection_id)}

@router.post("/api/v1/webhooks/unipile/new-message")
async def handle_new_message_webhook(request: Request):
    """Handle new LinkedIn message from Unipile"""
    body = await request.body()
    
    # Verify signature
    if not await verify_webhook_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    data = json.loads(body)
    
    # Extract message data
    account_id = data.get("account_id")
    account_type = data.get("account_type")
    event = data.get("event")  # message_received, message_reaction, etc.
    chat_id = data.get("chat_id")
    message_id = data.get("message_id")
    message_text = data.get("message")
    sender = data.get("sender", {})
    timestamp = data.get("timestamp")
    
    if account_type != "LINKEDIN":
        return {"status": "ignored", "reason": "Not a LinkedIn account"}
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Get LinkedIn connection
        connection = await conn.fetchrow("""
            SELECT id, company_id
            FROM linkedin_connections
            WHERE unipile_account_id = $1
        """, account_id)
        
        if not connection:
            logger.error(f"No LinkedIn connection found for account {account_id}")
            return {"status": "error", "reason": "Connection not found"}
        
        # Check if chat exists, create if not
        chat = await conn.fetchrow("""
            SELECT id FROM linkedin_chats
            WHERE unipile_chat_id = $1
        """, chat_id)
        
        if not chat:
            # Create new chat record
            chat_id_db = await conn.fetchval("""
                INSERT INTO linkedin_chats (
                    unipile_chat_id, linkedin_connection_id,
                    last_message_at
                ) VALUES ($1, $2, $3)
                RETURNING id
            """, chat_id, connection['id'], timestamp)
        else:
            chat_id_db = chat['id']
            # Update last message time
            await conn.execute("""
                UPDATE linkedin_chats
                SET last_message_at = $1, updated_at = $2
                WHERE id = $3
            """, timestamp, datetime.utcnow(), chat_id_db)
        
        if event == "message_received":
            # Store the message
            await conn.execute("""
                INSERT INTO linkedin_messages (
                    unipile_message_id, chat_id, provider_message_id,
                    sender_id, sender_name, message_text, is_sender,
                    sent_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (unipile_message_id) DO NOTHING
            """, 
            message_id, chat_id_db, message_id,
            sender.get("attendee_provider_id"), sender.get("attendee_name"),
            message_text, sender.get("attendee_provider_id") == data.get("account_info", {}).get("user_id"),
            timestamp
            )
            
            # Check if this is a reply to a campaign message
            campaign_log = await conn.fetchrow("""
                SELECT cl.*, c.auto_reply_enabled
                FROM linkedin_campaign_logs cl
                JOIN campaigns c ON cl.campaign_id = c.id
                WHERE cl.chat_id = $1 AND cl.has_replied = FALSE
            """, chat_id_db)
            
            if campaign_log and not campaign_log['has_replied']:
                # Mark as replied
                await conn.execute("""
                    UPDATE linkedin_campaign_logs
                    SET has_replied = TRUE
                    WHERE id = $1
                """, campaign_log['id'])
                
                # TODO: Handle auto-reply if enabled
                if campaign_log['auto_reply_enabled']:
                    logger.info(f"Auto-reply needed for chat {chat_id}")
        
        elif event == "message_read":
            # Update message as seen
            await conn.execute("""
                UPDATE linkedin_messages
                SET seen = TRUE
                WHERE unipile_message_id = $1
            """, message_id)
    
    return {"status": "success"}

# Register webhook routes in main.py
# app.include_router(unipile_webhooks.router)
