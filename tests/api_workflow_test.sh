#!/bin/bash

# API Workflow Test Script for ReachGenie
# This script tests the complete workflow:
# 1. Sign up a user
# 2. Login user
# 3. Create company
# 4. Create a product
# 5. Add a prospect
# 6. Create and run the campaign
# 7. Validate that the email and call are sent

# Set the base URL (change as needed for local or production environment)
BASE_URL=${API_URL:-"http://localhost:8001"}
echo "Using API URL: $BASE_URL"

# Set verbose mode for more detailed error information
VERBOSE=${VERBOSE:-false}
TIMEOUT=${TIMEOUT:-30}  # Default timeout of 30 seconds for curl requests

# Generate a random number for unique email addresses
RANDOM_NUM=$(date +%s)
echo "Using random number for unique emails: $RANDOM_NUM"

# Test user credentials - using a simpler email format to avoid issues with special characters
EMAIL="ashaheen+test${RANDOM_NUM}@workhub.ai"
PASSWORD="Test@123456"
NAME="Test User"

# Test prospect - using a simpler email format for the prospect as well
PROSPECT_EMAIL="ashaheen+prospect${RANDOM_NUM}@workhub.ai"
PROSPECT_PHONE="+4915151633365"
PROSPECT_NAME="Ahmed Shaheen"
PROSPECT_COMPANY="Test Company"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Function to print section headers
print_header() {
  echo ""
  echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to print verbose information if verbose mode is enabled
print_verbose() {
  if [ "$VERBOSE" = true ]; then
    echo -e "${YELLOW}[VERBOSE] $1${NC}"
  fi
}

# Function to make a curl request with better error handling
make_request() {
  local method=$1
  local url=$2
  local headers=("${@:3}")
  
  print_verbose "Making $method request to: $url"
  print_verbose "Headers: ${headers[@]}"
  
  # Build the curl command with the method and URL
  local curl_cmd="curl -s -X $method \"$url\" -m $TIMEOUT"
  
  # Add headers
  for header in "${headers[@]}"; do
    curl_cmd+=" -H \"$header\""
  done
  
  # If the method is POST or PUT and there's a data argument, add it
  if [ "$method" = "POST" ] || [ "$method" = "PUT" ]; then
    if [ ! -z "$4" ]; then
      curl_cmd+=" -d '$4'"
      print_verbose "Request Body: $4"
    fi
  fi
  
  print_verbose "Executing: $curl_cmd"
  
  # Execute the command and store the response
  local response=$(eval $curl_cmd)
  local status=$?
  
  print_verbose "Response: $response"
  print_verbose "Status: $status"
  
  echo "$response"
  return $status
}

# Function to check if a request was successful
check_success() {
  if [ $1 -eq 0 ] && [[ $2 == *"$3"* ]]; then
    echo -e "${GREEN}✓ Success: $4${NC}"
    return 0
  else
    echo -e "${RED}✗ Failed: $4 (Status: $1)${NC}"
    echo "Response: $2"
    return 1
  fi
}

# Save output files in a temporary directory
TEMP_DIR=$(mktemp -d)
echo "Temporary files will be stored in: $TEMP_DIR"

# 1. Sign up a user
print_header "SIGNING UP USER"
echo "Signing up user with email: $EMAIL"
SIGNUP_DATA="{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"name\":\"$NAME\"}"
SIGNUP_RESPONSE=$(make_request "POST" "$BASE_URL/api/auth/signup" "Content-Type: application/json" "$SIGNUP_DATA")

echo "Signup Response: $SIGNUP_RESPONSE"
check_success $? "$SIGNUP_RESPONSE" "success" "User signup"

# 2. Verify email (we'll simulate this since we can't actually click the link)
print_header "VERIFYING EMAIL"
echo "In a real scenario, the user would click the verification link sent to their email."
echo "For testing purposes, we'll use the resend verification endpoint and then directly check the database."

# For testing, you may need to manually set the verification status in the database
echo "You may need to manually set the user's verified status to true in the database before continuing."
echo "Example SQL: UPDATE users SET is_verified = true WHERE email = '$EMAIL';"

read -p "Press Enter after manually verifying the user to continue..." DUMMY

# 3. Login user
print_header "LOGGING IN USER"
LOGIN_DATA="username=$EMAIL&password=$PASSWORD"
LOGIN_RESPONSE=$(make_request "POST" "$BASE_URL/api/auth/login" "Content-Type: application/x-www-form-urlencoded" "$LOGIN_DATA")

echo "Login Response: $LOGIN_RESPONSE"
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}✗ Failed to extract access token${NC}"
  exit 1
else
  echo -e "${GREEN}✓ Successfully obtained access token${NC}"
  echo "Access Token: ${ACCESS_TOKEN:0:20}..."
fi

# 4. Create company
print_header "CREATING COMPANY"
COMPANY_DATA="{\"name\":\"Test Company\",\"website\":\"https://example.com\"}"
COMPANY_RESPONSE=$(make_request "POST" "$BASE_URL/api/companies" "Content-Type: application/json" "Authorization: Bearer $ACCESS_TOKEN" "$COMPANY_DATA")

echo "Company Response: $COMPANY_RESPONSE"
COMPANY_ID=$(echo $COMPANY_RESPONSE | grep -o '"id":"[^"]*' | sed 's/"id":"//')

check_success $? "$COMPANY_RESPONSE" "id" "Company creation"
echo "Company ID: $COMPANY_ID"

# 5. Create a product (using form-data for file upload)
print_header "CREATING PRODUCT"
# Use our sample text file for testing
echo "Creating a product with file: tests/sample_product.pdf.txt"
PRODUCT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/companies/$COMPANY_ID/products" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "product_name=Test Product" \
  -F "file=@tests/sample_product.pdf.txt" \
  -m $TIMEOUT)

echo "Product Response: $PRODUCT_RESPONSE"
PRODUCT_ID=$(echo $PRODUCT_RESPONSE | grep -o '"id":"[^"]*' | sed 's/"id":"//')

check_success $? "$PRODUCT_RESPONSE" "id" "Product creation"
echo "Product ID: $PRODUCT_ID"

# 6. Add a prospect
print_header "ADDING PROSPECT"
echo "Adding prospect with email: $PROSPECT_EMAIL"
LEAD_DATA="{\"name\":\"$PROSPECT_NAME\",\"email\":\"$PROSPECT_EMAIL\",\"phone\":\"$PROSPECT_PHONE\",\"company\":\"$PROSPECT_COMPANY\",\"title\":\"Test Title\",\"company_size\":\"10-50\",\"industry\":\"Technology\"}"
LEAD_RESPONSE=$(make_request "POST" "$BASE_URL/api/companies/$COMPANY_ID/leads" "Content-Type: application/json" "Authorization: Bearer $ACCESS_TOKEN" "$LEAD_DATA")

echo "Lead Response: $LEAD_RESPONSE"
LEAD_ID=$(echo $LEAD_RESPONSE | grep -o '"id":"[^"]*' | sed 's/"id":"//')

check_success $? "$LEAD_RESPONSE" "id" "Lead creation"
echo "Lead ID: $LEAD_ID"

# 7. Create a campaign
print_header "CREATING CAMPAIGN"
CAMPAIGN_DATA="{\"name\":\"Test Campaign\",\"type\":\"email\",\"leads\":[\"$LEAD_ID\"],\"template\":\"We are excited to tell you about our product {product_name}. It's amazing!\",\"subject\":\"Exciting news about our product\",\"product_id\":\"$PRODUCT_ID\"}"
CAMPAIGN_RESPONSE=$(make_request "POST" "$BASE_URL/api/companies/$COMPANY_ID/campaigns" "Content-Type: application/json" "Authorization: Bearer $ACCESS_TOKEN" "$CAMPAIGN_DATA")

echo "Campaign Response: $CAMPAIGN_RESPONSE"
CAMPAIGN_ID=$(echo $CAMPAIGN_RESPONSE | grep -o '"id":"[^"]*' | sed 's/"id":"//')

check_success $? "$CAMPAIGN_RESPONSE" "id" "Campaign creation"
echo "Campaign ID: $CAMPAIGN_ID"

# 8. Run the campaign
print_header "RUNNING CAMPAIGN"
RUN_CAMPAIGN_RESPONSE=$(make_request "POST" "$BASE_URL/api/campaigns/$CAMPAIGN_ID/run" "Authorization: Bearer $ACCESS_TOKEN")

echo "Run Campaign Response: $RUN_CAMPAIGN_RESPONSE"
check_success $? "$RUN_CAMPAIGN_RESPONSE" "success" "Running campaign"

# 9. Validate that the email was sent
print_header "VALIDATING EMAIL SENDING"
echo "Waiting 10 seconds for the campaign to process..."
sleep 10

# Get emails for the company
EMAILS_RESPONSE=$(make_request "GET" "$BASE_URL/api/companies/$COMPANY_ID/emails?campaign_id=$CAMPAIGN_ID" "Authorization: Bearer $ACCESS_TOKEN")

echo "Email Logs Response: $EMAILS_RESPONSE"
EMAIL_COUNT=$(echo $EMAILS_RESPONSE | grep -o '"id"' | wc -l)

if [ "$EMAIL_COUNT" -gt 0 ]; then
  echo -e "${GREEN}✓ Success: Found $EMAIL_COUNT email logs for the campaign${NC}"
else
  echo -e "${RED}✗ Failed: No email logs found for the campaign${NC}"
fi

# 10. Run the email processor script to check email processing
print_header "RUNNING EMAIL PROCESSOR SCRIPT"
echo "Running the email processor script to fetch emails..."

if [ -f "src/scripts/run_email_processor.py" ]; then
  python src/scripts/run_email_processor.py
  check_success $? "" "" "Email processor script execution"
else
  echo -e "${RED}✗ Email processor script not found${NC}"
fi

# 11. Create a call campaign
print_header "CREATING CALL CAMPAIGN"
CALL_CAMPAIGN_DATA="{\"name\":\"Test Call Campaign\",\"type\":\"call\",\"leads\":[\"$LEAD_ID\"],\"script\":\"Hello, I'm calling about our amazing product. Would you like to know more?\",\"product_id\":\"$PRODUCT_ID\"}"
CALL_CAMPAIGN_RESPONSE=$(make_request "POST" "$BASE_URL/api/companies/$COMPANY_ID/campaigns" "Content-Type: application/json" "Authorization: Bearer $ACCESS_TOKEN" "$CALL_CAMPAIGN_DATA")

echo "Call Campaign Response: $CALL_CAMPAIGN_RESPONSE"
CALL_CAMPAIGN_ID=$(echo $CALL_CAMPAIGN_RESPONSE | grep -o '"id":"[^"]*' | sed 's/"id":"//')

check_success $? "$CALL_CAMPAIGN_RESPONSE" "id" "Call campaign creation"
echo "Call Campaign ID: $CALL_CAMPAIGN_ID"

# 12. Run the call campaign
print_header "RUNNING CALL CAMPAIGN"
RUN_CALL_CAMPAIGN_RESPONSE=$(make_request "POST" "$BASE_URL/api/campaigns/$CALL_CAMPAIGN_ID/run" "Authorization: Bearer $ACCESS_TOKEN")

echo "Run Call Campaign Response: $RUN_CALL_CAMPAIGN_RESPONSE"
check_success $? "$RUN_CALL_CAMPAIGN_RESPONSE" "success" "Running call campaign"

# 13. Check calls after running the campaign
print_header "CHECKING CALLS"
echo "Waiting 10 seconds for the call campaign to process..."
sleep 10

CALLS_RESPONSE=$(make_request "GET" "$BASE_URL/api/companies/$COMPANY_ID/calls?campaign_id=$CALL_CAMPAIGN_ID" "Authorization: Bearer $ACCESS_TOKEN")

echo "Calls Response: $CALLS_RESPONSE"
CALL_COUNT=$(echo $CALLS_RESPONSE | grep -o '"id"' | wc -l)

if [ "$CALL_COUNT" -gt 0 ]; then
  echo -e "${GREEN}✓ Success: Found $CALL_COUNT call logs for the campaign${NC}"
else
  echo -e "${RED}✗ Failed: No call logs found for the campaign${NC}"
fi

# Summary
print_header "TEST SUMMARY"
echo "Test completed! Check the output above to see if all steps were successful."
echo "Temporary files were stored in: $TEMP_DIR" 