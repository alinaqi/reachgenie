#!/usr/bin/env python3
"""
Comprehensive Mailjet configuration diagnostics script
This script checks your Mailjet configuration and credentials
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

# Add the parent directory to sys.path to import modules from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Load environment variables from .env file
load_dotenv()

def check_required_env_vars():
    """Check if all required environment variables are set"""
    required_vars = [
        "MAILJET_API_KEY",
        "MAILJET_API_SECRET",
        "MAILJET_SENDER_EMAIL",
        "MAILJET_SENDER_NAME"
    ]
    
    print("=== Checking Required Environment Variables ===")
    all_present = True
    
    for var in required_vars:
        value = os.getenv(var, "")
        is_present = bool(value)
        status = "✓" if is_present else "✗"
        
        # Mask the value for security if present
        masked_value = ""
        if is_present:
            if var.endswith("_KEY") or var.endswith("_SECRET"):
                masked_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "****"
            else:
                masked_value = value
                
        print(f"{var}: {status} {masked_value}")
        
        if not is_present:
            all_present = False
    
    return all_present

def check_mailjet_account_status():
    """Check if the Mailjet account is active and credentials are valid"""
    api_key = os.getenv("MAILJET_API_KEY", "")
    api_secret = os.getenv("MAILJET_API_SECRET", "")
    
    if not api_key or not api_secret:
        print("\n=== Cannot Check Mailjet Account: Missing Credentials ===")
        return False
    
    print("\n=== Checking Mailjet Account Status ===")
    
    # Try to get account information
    url = "https://api.mailjet.com/v3/REST/user"
    
    try:
        response = requests.get(url, auth=(api_key, api_secret))
        
        print(f"API Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Successfully authenticated with Mailjet API")
            
            # Parse account details
            data = response.json()
            if "Data" in data and len(data["Data"]) > 0:
                user_data = data["Data"][0]
                print(f"Account Email: {user_data.get('Email', 'N/A')}")
                print(f"Account Status: {user_data.get('Status', 'N/A')}")
                print(f"Account Creation Date: {user_data.get('CreatedAt', 'N/A')}")
                
                return True
            else:
                print("✗ Could not retrieve account details")
                return False
        elif response.status_code == 401:
            print("✗ Authentication failed: Invalid API credentials")
            print(f"Error Response: {response.text}")
            return False
        else:
            print(f"✗ Unexpected response from Mailjet API: {response.status_code}")
            print(f"Error Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error connecting to Mailjet API: {str(e)}")
        return False

def check_sender_verification():
    """Check if the sender email is verified in Mailjet"""
    api_key = os.getenv("MAILJET_API_KEY", "")
    api_secret = os.getenv("MAILJET_API_SECRET", "")
    sender_email = os.getenv("MAILJET_SENDER_EMAIL", "")
    
    if not api_key or not api_secret or not sender_email:
        print("\n=== Cannot Check Sender Verification: Missing Information ===")
        return False
    
    print("\n=== Checking Sender Email Verification ===")
    print(f"Checking if {sender_email} is verified...")
    
    # Try to get sender information
    url = f"https://api.mailjet.com/v3/REST/sender?Email={sender_email}"
    
    try:
        response = requests.get(url, auth=(api_key, api_secret))
        
        print(f"API Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if "Data" in data and len(data["Data"]) > 0:
                sender_data = data["Data"][0]
                is_verified = sender_data.get("Status", "") == "Active"
                
                if is_verified:
                    print(f"✓ Sender email {sender_email} is verified and active")
                    return True
                else:
                    print(f"✗ Sender email {sender_email} is NOT verified (Status: {sender_data.get('Status', 'Unknown')})")
                    print("  You need to verify this sender email in your Mailjet account.")
                    print("  Go to: https://app.mailjet.com/account/sender")
                    return False
            else:
                print(f"✗ Sender email {sender_email} was not found in your Mailjet account")
                print("  You need to add and verify this sender email in your Mailjet account.")
                print("  Go to: https://app.mailjet.com/account/sender")
                return False
                
        else:
            print(f"✗ Could not check sender verification: {response.status_code}")
            print(f"Error Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error checking sender verification: {str(e)}")
        return False

def check_sending_limits():
    """Check Mailjet account sending limits"""
    api_key = os.getenv("MAILJET_API_KEY", "")
    api_secret = os.getenv("MAILJET_API_SECRET", "")
    
    if not api_key or not api_secret:
        print("\n=== Cannot Check Sending Limits: Missing Credentials ===")
        return
    
    print("\n=== Checking Mailjet Sending Limits ===")
    
    # Try to get account information
    url = "https://api.mailjet.com/v3/REST/user"
    
    try:
        response = requests.get(url, auth=(api_key, api_secret))
        
        if response.status_code == 200:
            data = response.json()
            if "Data" in data and len(data["Data"]) > 0:
                user_data = data["Data"][0]
                
                if "CreditsAvailable" in user_data:
                    print(f"Credits Available: {user_data['CreditsAvailable']}")
                if "LimitPerDay" in user_data:
                    print(f"Daily Send Limit: {user_data['LimitPerDay']} emails")
                    
                # Check if account is in production or sandbox mode
                if user_data.get('Status', '') == 'Sandbox':
                    print("⚠️ Account is in SANDBOX mode - emails can only be sent to verified addresses")
                    print("  To exit sandbox mode, visit: https://app.mailjet.com/account/billing")
                    
                return
            else:
                print("✗ Could not retrieve account details")
                return
        else:
            print(f"✗ Could not check sending limits: {response.status_code}")
            return
            
    except Exception as e:
        print(f"✗ Error checking sending limits: {str(e)}")
        return

def main():
    """Run all diagnostics"""
    print("=== Mailjet Configuration Diagnostic Tool ===\n")
    
    # Step 1: Check environment variables
    env_vars_ok = check_required_env_vars()
    
    # Step 2: Check Mailjet account status
    account_ok = check_mailjet_account_status()
    
    # Step 3: Check sender verification
    sender_ok = check_sender_verification()
    
    # Step 4: Check sending limits
    check_sending_limits()
    
    # Summary
    print("\n=== Diagnostic Summary ===")
    print(f"Environment Variables: {'✓ OK' if env_vars_ok else '✗ ISSUES FOUND'}")
    print(f"Mailjet Account Status: {'✓ OK' if account_ok else '✗ ISSUES FOUND'}")
    print(f"Sender Verification: {'✓ OK' if sender_ok else '✗ ISSUES FOUND'}")
    
    if env_vars_ok and account_ok and sender_ok:
        print("\n✅ Your Mailjet configuration appears to be correct.")
        print("   If you're still having issues sending emails, check your application logs for specific error messages.")
    else:
        print("\n⚠️ Issues were found with your Mailjet configuration.")
        print("   Please review the details above and make necessary corrections.")
        
        if not env_vars_ok:
            print("   - Make sure all required environment variables are set in your .env file")
        if not account_ok:
            print("   - Verify your Mailjet API credentials")
        if not sender_ok:
            print("   - Verify your sender email in the Mailjet dashboard")

if __name__ == "__main__":
    main() 