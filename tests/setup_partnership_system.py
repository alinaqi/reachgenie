#!/usr/bin/env python3
import os
import sys
import logging
import requests
from dotenv import load_dotenv

# Add the parent directory to the path so Python can find our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def run_migration():
    """Run the partner applications migration"""
    try:
        # Import here after sys.path is set up
        from migrations.run_migration import run_migration as migrate
        
        logger.info("Running partner application database migration...")
        migrate()
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Error running migration: {str(e)}")
        logger.exception(e)

def verify_perplexity_api_key():
    """Verify that the Perplexity API key is valid by making a test request"""
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not perplexity_key:
        logger.error("⚠️ PERPLEXITY_API_KEY not set in environment variables")
        return False
    
    logger.info("Testing Perplexity API key...")
    
    try:
        # Make a simple request to verify the API key
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {perplexity_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar",
                "messages": [{"role": "user", "content": "Hello! Just testing the API key."}]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("✅ Perplexity API key is valid")
            return True
        else:
            logger.error(f"❌ Perplexity API key verification failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Error testing Perplexity API key: {str(e)}")
        return False

def setup_env():
    """Check if required environment variables are set up"""
    # Check Mailjet configuration
    mailjet_vars = {
        "MAILJET_API_KEY": os.getenv("MAILJET_API_KEY"),
        "MAILJET_API_SECRET": os.getenv("MAILJET_API_SECRET"),
        "MAILJET_SENDER_EMAIL": os.getenv("MAILJET_SENDER_EMAIL"),
        "MAILJET_SENDER_NAME": os.getenv("MAILJET_SENDER_NAME")
    }
    
    logger.info("Checking Mailjet configuration...")
    missing_mailjet = [key for key, value in mailjet_vars.items() if not value]
    
    if missing_mailjet:
        logger.warning(f"Missing Mailjet environment variables: {', '.join(missing_mailjet)}")
        logger.warning("Please set these variables in your .env file for email functionality")
    else:
        logger.info("✅ Mailjet configuration looks good")
    
    # Check AI API keys
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not perplexity_key:
        logger.error("⚠️ PERPLEXITY_API_KEY not set - company research will not work")
        logger.error("  → Get your key at https://docs.perplexity.ai/")
    else:
        # Verify the Perplexity API key is valid
        if not verify_perplexity_api_key():
            logger.error("⚠️ Perplexity API key verification failed - please check your key")
        
    if not openai_key:
        logger.warning("⚠️ OPENAI_API_KEY not set - personalized email generation will not work")
        logger.warning("  → Get your key at https://platform.openai.com/api-keys")
    else:
        logger.info("✅ OpenAI API key is configured")
        
    # Check test email is set
    test_email = os.getenv("TEST_EMAIL")
    if not test_email:
        logger.warning("⚠️ TEST_EMAIL not set - add this for testing partnership emails")
    else:
        logger.info(f"✅ Test email configured: {test_email}")
        
    if perplexity_key and openai_key and not missing_mailjet:
        logger.info("✅ All required environment variables are set for partnership system")
    else:
        logger.warning("⚠️ Some environment variables are missing - partnership emails may not work correctly")

if __name__ == "__main__":
    logger.info("Setting up ReachGenie Partnership System...")
    setup_env()
    run_migration()
    
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Test the full partnership email flow: python tests/test_partner_email.py")
    logger.info("2. Start the server: uvicorn src.main:app --reload")
    logger.info("3. Submit a test application through the API") 