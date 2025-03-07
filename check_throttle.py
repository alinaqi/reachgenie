import asyncio
from uuid import UUID
from src.database import get_email_throttle_settings

async def check_throttle():
    company_id = UUID('a7e85ef3-388a-44c0-988b-c848336e02aa')
    settings = await get_email_throttle_settings(company_id)
    
    print('Current throttle settings:')
    print(f'Max emails per hour: {settings.get("max_emails_per_hour", 500)}')
    print(f'Max emails per day: {settings.get("max_emails_per_day", 500)}')
    print(f'Throttling enabled: {settings.get("enabled", True)}')

if __name__ == "__main__":
    asyncio.run(check_throttle()) 