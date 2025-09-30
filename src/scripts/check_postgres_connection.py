import asyncpg
from asyncpg.pool import Pool
import asyncio
import logging
from typing import Optional
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PostgreSQL connection pool
pg_pool: Optional[Pool] = None

async def init_pg_pool():
    global pg_pool
    if pg_pool is None:
        try:
            pg_pool = await asyncpg.create_pool(
                user=os.getenv('POSTGRES_USER'),
                password=os.getenv('POSTGRES_PASSWORD'),
                database=os.getenv('POSTGRES_DB'),
                host=os.getenv('POSTGRES_HOST'),
                port=int(os.getenv('POSTGRES_PORT', '5432')),
                min_size=1,
                max_size=10
            )
            logger.info("PostgreSQL connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL connection pool: {str(e)}")
            raise

async def get_pg_pool() -> Pool:
    if pg_pool is None:
        await init_pg_pool()
    return pg_pool

async def check_postgres_connection():
    pool = await get_pg_pool()

    count_sql = """
                    SELECT COUNT(*) 
                    FROM leads
                """
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql)
        logger.info(f"Total leads: {total}")
        return total

if __name__ == "__main__":
    asyncio.run(check_postgres_connection())