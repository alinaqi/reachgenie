#!/bin/bash
# Test script for checking the API endpoints

echo "This test script will:"
echo "1. Login with provided credentials"
echo "2. Call /api/companies?show_stats=true"
echo "3. Show the response"
echo ""
echo "Enter email (or press Enter for default: ashaheen@workhub.ai):"
read EMAIL
if [ -z "$EMAIL" ]; then
    EMAIL="ashaheen@workhub.ai"
fi

echo "Enter password:"
read -s PASSWORD
echo ""

# Login
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

# Extract token using grep and sed
TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -z "$TOKEN" ]; then
    echo "Login failed. Response:"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

echo "Login successful. Token obtained."
echo ""

# Get user info
echo "Getting user info (/api/users/me)..."
ME_RESPONSE=$(curl -s -X GET "http://localhost:8001/api/users/me" \
    -H "Authorization: Bearer $TOKEN")

echo "User info:"
echo "$ME_RESPONSE" | python3 -m json.tool | head -20
echo ""

# Get companies without stats
echo "Getting companies without stats (/api/companies)..."
COMPANIES_RESPONSE=$(curl -s -X GET "http://localhost:8001/api/companies" \
    -H "Authorization: Bearer $TOKEN")

echo "Companies count (without stats):"
echo "$COMPANIES_RESPONSE" | python3 -c "import json, sys; data = json.load(sys.stdin); print(f'Found {len(data)} companies')"
echo ""

# Get companies with stats
echo "Getting companies with stats (/api/companies?show_stats=true)..."
COMPANIES_STATS_RESPONSE=$(curl -s -X GET "http://localhost:8001/api/companies?show_stats=true" \
    -H "Authorization: Bearer $TOKEN")

echo "Companies count (with stats):"
echo "$COMPANIES_STATS_RESPONSE" | python3 -c "import json, sys; data = json.load(sys.stdin); print(f'Found {len(data)} companies')"

if [ "$COMPANIES_STATS_RESPONSE" != "[]" ]; then
    echo ""
    echo "First company details:"
    echo "$COMPANIES_STATS_RESPONSE" | python3 -m json.tool | head -30
fi

# Debug endpoint
echo ""
echo "Getting debug info (/api/debug/companies)..."
DEBUG_RESPONSE=$(curl -s -X GET "http://localhost:8001/api/debug/companies" \
    -H "Authorization: Bearer $TOKEN")

echo "Debug response (summary):"
echo "$DEBUG_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'User ID: {data.get(\"user_id\", \"N/A\")}')
    print(f'Company roles count: {len(data.get(\"company_roles\", []))}')
    print(f'User company profiles count: {data.get(\"user_company_profiles_count\", \"N/A\")}')
    print(f'Companies with join count: {data.get(\"companies_with_join_count\", \"N/A\")}')
except:
    print('Error parsing debug response')
    print(sys.stdin.read())
"
