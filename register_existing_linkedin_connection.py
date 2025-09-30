"""
Register an existing Unipile LinkedIn connection in ReachGenie database
"""
import asyncio
from uuid import UUID
from datetime import datetime
from src.database import get_pg_pool
from src.services.linkedin_service import linkedin_service
import json

async def register_existing_connection(
    unipile_account_id: str,
    company_id: str,
    user_email: str
):
    """Register an existing Unipile LinkedIn connection"""
    pool = await get_pg_pool()
    
    async with pool.acquire() as conn:
        # First, get the user
        user = await conn.fetchrow(
            "SELECT id, channels_active FROM users WHERE email = $1",
            user_email
        )
        
        if not user:
            print(f"❌ User {user_email} not found")
            return
            
        # Enable LinkedIn channel for the user
        channels = user['channels_active'] or {}
        channels['linkedin'] = True
        
        await conn.execute(
            """
            UPDATE users 
            SET channels_active = $1
            WHERE id = $2
            """,
            json.dumps(channels),
            user['id']
        )
        print(f"✅ LinkedIn channel enabled for {user_email}")
        
        # Get account info from Unipile
        try:
            account_info = await linkedin_service.get_account_info(unipile_account_id)
            print(f"✅ Found LinkedIn account: {account_info.get('name', 'Unknown')}")
        except Exception as e:
            print(f"⚠️  Could not fetch account info from Unipile: {e}")
            account_info = {}
        
        # Check if connection already exists
        existing = await conn.fetchrow(
            "SELECT id FROM linkedin_connections WHERE unipile_account_id = $1",
            unipile_account_id
        )
        
        if existing:
            print(f"⚠️  Connection already exists with ID: {existing['id']}")
            # Update the status to active
            await conn.execute(
                """
                UPDATE linkedin_connections
                SET account_status = 'OK',
                    updated_at = NOW()
                WHERE id = $1
                """,
                existing['id']
            )
            print("✅ Updated connection status to OK")
        else:
            # Insert new connection
            connection_id = await conn.fetchval(
                """
                INSERT INTO linkedin_connections (
                    company_id,
                    unipile_account_id,
                    account_email,
                    account_name,
                    account_status,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                RETURNING id
                """,
                UUID(company_id),
                unipile_account_id,
                account_info.get('email', ''),
                account_info.get('name', ''),
                'OK'  # Active status
            )
            print(f"✅ Created new LinkedIn connection with ID: {connection_id}")
        
        # Optionally set as primary LinkedIn connection for the company
        await conn.execute(
            """
            UPDATE companies
            SET primary_linkedin_connection_id = (
                SELECT id FROM linkedin_connections 
                WHERE company_id = $1 AND account_status = 'OK'
                ORDER BY created_at DESC
                LIMIT 1
            )
            WHERE id = $1
            """,
            UUID(company_id)
        )
        print(f"✅ Set as primary LinkedIn connection for company")
        
        print("\n🎉 LinkedIn connection successfully registered!")
        print("You can now use this account for LinkedIn campaigns in ReachGenie")

if __name__ == "__main__":
    # EDIT THESE VALUES
    UNIPILE_ACCOUNT_ID = "82lsvTxjRZuPZIBtDYyezA"  # Your Unipile account ID
    COMPANY_ID = "YOUR_COMPANY_ID_HERE"  # Replace with your actual company ID
    USER_EMAIL = "your-email@example.com"  # Your email in ReachGenie
    
    asyncio.run(register_existing_connection(
        UNIPILE_ACCOUNT_ID,
        COMPANY_ID,
        USER_EMAIL
    ))
