"""
Quick script to enable LinkedIn channel for testing
Run this to enable LinkedIn in your user's channels_active
"""
import asyncio
from src.database import get_pg_pool
import json

async def enable_linkedin_channel(user_email: str):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        # Get current user
        user = await conn.fetchrow(
            "SELECT id, channels_active FROM users WHERE email = $1",
            user_email
        )
        
        if not user:
            print(f"User {user_email} not found")
            return
            
        # Update channels_active to include LinkedIn
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
        print(f"Channels active: {channels}")

if __name__ == "__main__":
    # Replace with your actual email
    USER_EMAIL = "your-email@example.com"
    
    asyncio.run(enable_linkedin_channel(USER_EMAIL))
