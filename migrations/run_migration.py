#!/usr/bin/env python3
import os
import logging
from supabase import create_client
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def run_migration():
    """
    Run the partner applications migration SQL file
    """
    # Get Supabase credentials from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for migrations
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials not found in environment variables")
        return
    
    try:
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Read migration SQL file
        migration_file = "partner_applications_tables.sql"
        migration_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), migration_file)
        
        with open(migration_path, 'r') as f:
            sql = f.read()
        
        # Execute the SQL
        logger.info(f"Running migration from {migration_file}")
        
        # Execute each statement separately
        for statement in sql.split(';'):
            if statement.strip():
                # Use the raw SQL query feature of Supabase
                result = supabase.rpc('exec_sql', {'query': statement}).execute()
                logger.info(f"Result: {result}")
        
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Error running migration: {str(e)}")

if __name__ == "__main__":
    run_migration() 