import os
import json
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(supabase_url, supabase_key)

def get_lead_count():
    """Get the total number of leads in the database"""
    response = supabase.table('leads')\
        .select('count', count='exact')\
        .is_('deleted_at', None)\
        .execute()
    return response.count

def get_latest_leads(limit=5):
    """Get the most recent leads from the database"""
    response = supabase.table('leads')\
        .select('*')\
        .is_('deleted_at', None)\
        .order('created_at', desc=True)\
        .limit(limit)\
        .execute()
    return response.data

def get_db_schema():
    # This function will help us understand the database structure
    # We'll use PostgreSQL's information_schema to list all tables
    response = supabase.rpc(
        'execute_sql', 
        {'query': """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """}
    ).execute()
    return response.data

def search_for_task_table():
    # This function will search for tables that might contain task information
    # by looking for tables with names containing 'task', 'job', 'queue', etc.
    tables = get_db_schema()
    task_related_tables = [t['table_name'] for t in tables if 
                          'task' in t['table_name'] or 
                          'job' in t['table_name'] or 
                          'queue' in t['table_name'] or
                          'background' in t['table_name'] or 
                          'process' in t['table_name']]
    return task_related_tables

if __name__ == "__main__":
    # Get and print lead count
    lead_count = get_lead_count()
    print(f"Total lead count: {lead_count}\n")
    
    # Get and print latest leads
    latest_leads = get_latest_leads()
    print("Latest leads:")
    for lead in latest_leads:
        print(f"ID: {lead.get('id')}")
        print(f"Name: {lead.get('name')}")
        print(f"Email: {lead.get('email')}")
        print(f"Company: {lead.get('company')}")
        print(f"Created at: {lead.get('created_at')}")
        print("---")
    
    # Check database schema
    print("\nDatabase schema:")
    tables = get_db_schema()
    for table in tables:
        print(f"- {table.get('table_name')}")
    
    # Search for task-related tables
    print("\nPotential task-related tables:")
    task_tables = search_for_task_table()
    if task_tables:
        for table in task_tables:
            print(f"- {table}")
    else:
        print("No task-related tables found.")
    
    # Commented out the failing function since the 'tasks' table doesn't exist
    # tasks = get_task_status()
    # print("\nRecent lead upload tasks:")
    # for task in tasks:
    #     print(f"ID: {task.get('id')}")
    #     print(f"Status: {task.get('status')}")
    #     print(f"Created at: {task.get('created_at')}")
    #     if task.get('result'):
    #         result = json.loads(task.get('result'))
    #         print(f"Result: {result}")
    #     print("---") 