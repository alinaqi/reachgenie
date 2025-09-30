"""
LinkedIn API routes for managing LinkedIn connections and campaigns
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timezone
from src.auth import get_current_user
# UserInDB import removed - using dict from get_current_user
from src.database import (
    supabase,
    get_user_company_profile,
    get_company_by_id
)
from src.services.linkedin_service import linkedin_service
from src.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

@router.post("/v1/linkedin/connect/simple")
async def simple_linkedin_connect_validated(
    request: Dict[str, str],
    current_user: dict = Depends(get_current_user)
):
    """Simple LinkedIn connection with just account ID"""
    company_id = request.get("company_id")
    unipile_account_id = request.get("unipile_account_id")
    
    if not company_id or not unipile_account_id:
        raise HTTPException(status_code=400, detail="Company ID and Account ID required")
    
    # Verify user has access to company
    user_profile = await get_user_company_profile(current_user["id"], UUID(company_id))
    if not user_profile:
        raise HTTPException(status_code=403, detail="Access denied to this company")
    
    # Simple validation - just check if it works
    try:
        account_info = await linkedin_service.get_account_info(unipile_account_id)
        
        if account_info.get("provider") != "LINKEDIN":
            raise HTTPException(status_code=400, detail="Not a LinkedIn account")
        
        # Check if connection already exists
        existing = supabase.table("linkedin_connections")\
            .select("id")\
            .eq("unipile_account_id", unipile_account_id)\
            .execute()
        
        if existing.data:
            # Update existing
            update_data = {
                "account_status": account_info.get("status", "OK"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if account_info.get("email"):
                update_data["connection_email"] = account_info["email"]
            if account_info.get("name"):
                update_data["display_name"] = account_info["name"]
                
            result = supabase.table("linkedin_connections")\
                .update(update_data)\
                .eq("id", existing.data[0]["id"])\
                .execute()
            connection_id = existing.data[0]["id"]
        else:
            # Insert new
            result = supabase.table("linkedin_connections")\
                .insert({
                    "company_id": str(company_id),
                    "unipile_account_id": unipile_account_id,
                    "connection_email": account_info.get("email", ""),
                    "display_name": account_info.get("name", ""),
                    "account_status": account_info.get("status", "OK"),
                    "account_type": "LINKEDIN"
                })\
                .execute()
            connection_id = result.data[0]["id"]
        
        return {"success": True, "connection_id": str(connection_id)}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/v1/linkedin/validate-account")
async def validate_linkedin_account(
    request: Dict[str, str],
    current_user: dict = Depends(get_current_user)
):
    """Validate a Unipile account ID"""
    unipile_account_id = request.get("unipile_account_id")
    
    if not unipile_account_id:
        raise HTTPException(status_code=400, detail="Account ID is required")
    
    try:
        # Get account info from Unipile
        account_info = await linkedin_service.get_account_info(unipile_account_id)
        
        # Check if it's a LinkedIn account
        is_linkedin = account_info.get("provider") == "LINKEDIN"
        
        return {
            "valid": True,
            "is_linkedin": is_linkedin,
            "account_info": {
                "name": account_info.get("name"),
                "email": account_info.get("email"),
                "provider": account_info.get("provider"),
                "status": account_info.get("status")
            }
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }

@router.post("/v1/linkedin/reconnect/{connection_id}")
async def reconnect_linkedin_account(
    connection_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Reconnect a disconnected LinkedIn account"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Get connection and verify access
        connection = await conn.fetchrow("""
            SELECT lc.*, c.user_id
            FROM linkedin_connections lc
            JOIN companies c ON lc.company_id = c.id
            JOIN users_companies uc ON c.id = uc.company_id
            WHERE lc.id = $1 AND uc.user_id = $2
        """, connection_id, current_user["id"])
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        if connection['account_status'] == 'OK':
            return {"message": "Account is already connected"}
    
    # Generate reconnection link
    success_url = f"{settings.frontend_url}/linkedin/reconnected"
    failure_url = f"{settings.frontend_url}/linkedin/reconnect-failed"
    
    try:
        result = await linkedin_service.reconnect_account(
            account_id=connection['unipile_account_id'],
            success_redirect_url=success_url,
            failure_redirect_url=failure_url
        )
        
        return {
            "auth_url": result["url"],
            "expires_in": 3600
        }
    except Exception as e:
        logger.error(f"Failed to reconnect LinkedIn account: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create reconnection link")

@router.get("/v1/linkedin/connections")
async def get_linkedin_connections(
    company_id: Optional[UUID] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get LinkedIn connections for user's companies"""
    if company_id:
        # Verify access to specific company
        user_profile = await get_user_company_profile(current_user["id"], company_id)
        if not user_profile:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get connections for specific company
        response = supabase.table("linkedin_connections")\
            .select("*, companies!linkedin_connections_company_id_fkey(name)")\
            .eq("company_id", str(company_id))\
            .order("created_at", desc=True)\
            .execute()
        
        connections = []
        for conn in response.data:
            conn_data = conn.copy()
            conn_data["company_name"] = conn.get("companies", {}).get("name", "")
            conn_data.pop("companies", None)
            connections.append(conn_data)
    else:
        # Get all connections for user's companies
        # First get user's companies
        from src.database import get_companies_by_user_id
        user_companies = await get_companies_by_user_id(current_user["id"])
        company_ids = [str(comp["id"]) for comp in user_companies]
        
        if not company_ids:
            return []
        
        # Get connections for all user's companies
        response = supabase.table("linkedin_connections")\
            .select("*, companies!linkedin_connections_company_id_fkey(name)")\
            .in_("company_id", company_ids)\
            .order("created_at", desc=True)\
            .execute()
        
        connections = []
        for conn in response.data:
            conn_data = conn.copy()
            conn_data["company_name"] = conn.get("companies", {}).get("name", "")
            conn_data.pop("companies", None)
            connections.append(conn_data)
    
    return connections

@router.delete("/v1/linkedin/connections/{connection_id}")
async def disconnect_linkedin_account(
    connection_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Disconnect a LinkedIn account"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Verify access to connection
        connection = await conn.fetchrow("""
            SELECT lc.*, c.id as company_id
            FROM linkedin_connections lc
            JOIN companies c ON lc.company_id = c.id
            JOIN users_companies uc ON c.id = uc.company_id
            WHERE lc.id = $1 AND uc.user_id = $2
        """, connection_id, current_user["id"])
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found or access denied")
        
        # Update connection status to inactive/disconnected
        await conn.execute("""
            UPDATE linkedin_connections
            SET 
                account_status = 'DISCONNECTED',
                updated_at = NOW()
            WHERE id = $1
        """, connection_id)
        
        # Optionally, you might want to disable related campaigns
        await conn.execute("""
            UPDATE campaigns
            SET 
                is_active = FALSE,
                updated_at = NOW()
            WHERE company_id = $1 
            AND type = 'linkedin'
            AND is_active = TRUE
        """, connection['company_id'])
        
        return {"message": "LinkedIn account disconnected successfully"}

@router.post("/v1/linkedin/sync-lead-profile")
async def sync_lead_linkedin_profile(
    lead_id: UUID,
    linkedin_url: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Sync LinkedIn profile data for a lead"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Verify access to lead
        lead = await conn.fetchrow("""
            SELECT l.*, c.primary_linkedin_connection_id, lc.unipile_account_id
            FROM leads l
            JOIN companies c ON l.company_id = c.id
            JOIN users_companies uc ON c.id = uc.company_id
            LEFT JOIN linkedin_connections lc ON c.primary_linkedin_connection_id = lc.id
            WHERE l.id = $1 AND uc.user_id = $2
        """, lead_id, current_user["id"])
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        if not lead['primary_linkedin_connection_id']:
            raise HTTPException(
                status_code=400, 
                detail="No LinkedIn account connected for this company"
            )
        
        if not lead['unipile_account_id']:
            raise HTTPException(
                status_code=400,
                detail="LinkedIn connection not properly configured"
            )
    
    # Use provided URL or existing one
    profile_url = linkedin_url or lead.get('personal_linkedin_url')
    if not profile_url and not lead.get('personal_linkedin_id'):
        raise HTTPException(
            status_code=400,
            detail="No LinkedIn profile URL or ID available for this lead"
        )
    
    try:
        result = await linkedin_service.sync_lead_linkedin_profile(
            lead_id=lead_id,
            account_id=lead['unipile_account_id'],
            linkedin_url=profile_url,
            provider_id=lead.get('personal_linkedin_id')
        )
        
        return {
            "status": "success",
            "message": "LinkedIn profile synced successfully",
            "profile_data": result["profile_data"]
        }
    except Exception as e:
        logger.error(f"Failed to sync LinkedIn profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/linkedin/campaign-stats/{campaign_id}")
async def get_linkedin_campaign_stats(
    campaign_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get LinkedIn campaign statistics"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Verify access to campaign
        campaign = await conn.fetchrow("""
            SELECT c.*, comp.name as company_name
            FROM campaigns c
            JOIN companies comp ON c.company_id = comp.id
            JOIN users_companies uc ON comp.id = uc.company_id
            WHERE c.id = $1 AND uc.user_id = $2
        """, campaign_id, current_user["id"])
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign statistics
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_sent,
                COUNT(CASE WHEN has_replied = TRUE THEN 1 END) as replied,
                COUNT(CASE WHEN has_accepted_invitation = TRUE THEN 1 END) as invitations_accepted,
                COUNT(CASE WHEN has_meeting_booked = TRUE THEN 1 END) as meetings_booked,
                MIN(sent_at) as first_sent,
                MAX(sent_at) as last_sent
            FROM linkedin_campaign_logs
            WHERE campaign_id = $1 AND sent_at IS NOT NULL
        """, campaign_id)
        
        # Get message breakdown
        messages = await conn.fetch("""
            SELECT 
                reminder_type,
                COUNT(*) as count
            FROM linkedin_messages
            WHERE campaign_id = $1
            GROUP BY reminder_type
        """, campaign_id)
        
        return {
            "campaign": dict(campaign),
            "stats": dict(stats),
            "message_breakdown": [dict(m) for m in messages],
            "reply_rate": (stats['replied'] / stats['total_sent'] * 100) if stats['total_sent'] > 0 else 0,
            "meeting_rate": (stats['meetings_booked'] / stats['total_sent'] * 100) if stats['total_sent'] > 0 else 0
        }

@router.get("/v1/linkedin/chats/{connection_id}")
async def get_linkedin_chats(
    connection_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get LinkedIn chats for a connection"""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Verify access
        connection = await conn.fetchrow("""
            SELECT lc.*
            FROM linkedin_connections lc
            JOIN companies c ON lc.company_id = c.id
            JOIN users_companies uc ON c.id = uc.company_id
            WHERE lc.id = $1 AND uc.user_id = $2
        """, connection_id, current_user["id"])
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Get chats with latest message
        chats = await conn.fetch("""
            SELECT 
                lc.*,
                lm.message_text as last_message,
                lm.sent_at as last_message_at,
                lm.is_sender as last_message_is_sender,
                COUNT(DISTINCT lm2.id) as message_count
            FROM linkedin_chats lc
            LEFT JOIN LATERAL (
                SELECT * FROM linkedin_messages
                WHERE chat_id = lc.id
                ORDER BY sent_at DESC
                LIMIT 1
            ) lm ON TRUE
            LEFT JOIN linkedin_messages lm2 ON lm2.chat_id = lc.id
            WHERE lc.linkedin_connection_id = $1
            GROUP BY lc.id, lm.message_text, lm.sent_at, lm.is_sender
            ORDER BY COALESCE(lm.sent_at, lc.created_at) DESC
            LIMIT $2 OFFSET $3
        """, connection_id, limit, offset)
        
        return [dict(chat) for chat in chats] if chats else []

@router.post("/v1/linkedin/campaigns")
async def create_linkedin_campaign(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Create a LinkedIn outreach campaign"""
    pool = await get_pg_pool()
    
    # Extract request data
    company_id = request.get("company_id")
    name = request.get("name")
    connection_id = request.get("connection_id")
    target_profiles = request.get("target_profiles", [])
    message_template = request.get("message_template")
    daily_limit = request.get("daily_limit", 50)
    
    if not all([company_id, name, connection_id, message_template]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    async with pool.acquire() as conn:
        # Verify access
        company = await conn.fetchrow("""
            SELECT c.* FROM companies c
            JOIN users_companies uc ON c.id = uc.company_id
            WHERE c.id = $1 AND uc.user_id = $2
        """, UUID(company_id), current_user["id"])
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Verify LinkedIn connection
        connection = await conn.fetchrow("""
            SELECT * FROM linkedin_connections
            WHERE id = $1 AND company_id = $2 AND account_status = 'OK'
        """, UUID(connection_id), UUID(company_id))
        
        if not connection:
            raise HTTPException(status_code=404, detail="LinkedIn connection not found or inactive")
        
        # Create campaign
        campaign_id = await conn.fetchval("""
            INSERT INTO campaigns (
                company_id,
                name,
                type,
                settings,
                is_active,
                created_at,
                updated_at,
                created_by
            ) VALUES ($1, $2, 'linkedin', $3, true, NOW(), NOW(), $4)
            RETURNING id
        """,
        UUID(company_id),
        name,
        {
            "connection_id": connection_id,
            "message_template": message_template,
            "daily_limit": daily_limit,
            "target_profiles": target_profiles
        },
        current_user["id"]
        )
        
        # Add target profiles to campaign_leads
        for profile in target_profiles:
            await conn.execute("""
                INSERT INTO campaign_leads (
                    campaign_id,
                    linkedin_profile_url,
                    status,
                    created_at
                ) VALUES ($1, $2, 'pending', NOW())
            """, campaign_id, profile.get("url"))
        
        return {
            "id": str(campaign_id),
            "message": "LinkedIn campaign created successfully",
            "target_count": len(target_profiles)
        }

@router.get("/v1/linkedin/campaigns/{company_id}")
async def get_linkedin_campaigns(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get LinkedIn campaigns for a company"""
    pool = await get_pg_pool()
    
    async with pool.acquire() as conn:
        # Verify access
        access = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM users_companies
                WHERE user_id = $1 AND company_id = $2
            )
        """, current_user["id"], company_id)
        
        if not access:
            raise HTTPException(status_code=403, detail="Access denied")
        
        campaigns = await conn.fetch("""
            SELECT 
                c.*,
                COUNT(cl.id) as total_leads,
                COUNT(CASE WHEN cl.status = 'sent' THEN 1 END) as sent_count,
                COUNT(CASE WHEN cl.status = 'replied' THEN 1 END) as reply_count
            FROM campaigns c
            LEFT JOIN campaign_leads cl ON c.id = cl.campaign_id
            WHERE c.company_id = $1 AND c.type = 'linkedin'
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """, company_id)
        
        return [dict(campaign) for campaign in campaigns]

@router.post("/v1/linkedin/simple-connect")
async def simple_linkedin_connect_minimal(
    request: Dict[str, str],
    current_user: dict = Depends(get_current_user)
):
    """Dead simple LinkedIn connection - just add account ID and go"""
    company_id = request.get("company_id")
    account_id = request.get("account_id")
    
    if not company_id or not account_id:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        try:
            # Just save it - validation happens when they try to use it
            connection_id = await conn.fetchval("""
                INSERT INTO linkedin_connections (
                    company_id, unipile_account_id, account_status
                ) VALUES ($1, $2, 'active')
                ON CONFLICT (unipile_account_id) DO UPDATE 
                SET company_id = $1, updated_at = NOW()
                RETURNING id
            """, UUID(company_id), account_id)
            
            return {"success": True, "connection_id": str(connection_id)}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/v1/linkedin/simple-connect")
async def api_simple_linkedin_connect(
    request: Dict[str, str],
    current_user: dict = Depends(get_current_user)
):
    """Simple LinkedIn connection - saves unipile account ID"""
    company_id = request.get("company_id")
    unipile_account_id = request.get("unipile_account_id") or request.get("account_id")
    
    if not company_id or not unipile_account_id:
        raise HTTPException(status_code=400, detail="Company ID and Unipile Account ID are required")
    
    # Verify user has access to company
    user_profile = await get_user_company_profile(current_user["id"], UUID(company_id))
    if not user_profile:
        raise HTTPException(status_code=404, detail="Company not found or access denied")
    
    try:
        # Optionally validate with Unipile (but don't fail if it doesn't work)
        account_info = {}
        try:
            account_info = await linkedin_service.get_account_info(unipile_account_id)
        except Exception as e:
            logger.warning(f"Could not validate account {unipile_account_id}: {e}")
            # Continue anyway - we'll validate when they actually use it
        
        # Check if connection already exists
        existing = supabase.table("linkedin_connections")\
            .select("id, connection_email, display_name")\
            .eq("unipile_account_id", unipile_account_id)\
            .execute()
        
        if existing.data:
            # Update existing connection
            update_data = {
                "company_id": str(company_id),
                "account_status": account_info.get("status", "active"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            # Only update email/name if we got new values
            if account_info.get("email"):
                update_data["connection_email"] = account_info["email"]
            if account_info.get("name"):
                update_data["display_name"] = account_info["name"]
                
            result = supabase.table("linkedin_connections")\
                .update(update_data)\
                .eq("id", existing.data[0]["id"])\
                .execute()
            connection_id = existing.data[0]["id"]
        else:
            # Insert new connection
            result = supabase.table("linkedin_connections")\
                .insert({
                    "company_id": str(company_id),
                    "unipile_account_id": unipile_account_id,
                    "connection_email": account_info.get("email", ""),
                    "display_name": account_info.get("name", ""),
                    "account_status": account_info.get("status", "active"),
                    "account_type": "LINKEDIN"
                })\
                .execute()
            connection_id = result.data[0]["id"]
        
        return {
            "success": True, 
            "connection_id": str(connection_id),
            "message": "LinkedIn account connected successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to save LinkedIn connection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save connection: {str(e)}")

# Register routes in main.py
# app.include_router(linkedin.router)
