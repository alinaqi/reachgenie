# API Workflow Test Scripts

This directory contains automated test scripts that verify the complete API workflow for ReachGenie:

1. User signup
2. User login
3. Company creation
4. Product creation
5. Adding a prospect
6. Creating and running email and call campaigns
7. Validating that emails and calls are sent

## Available Test Scripts

### 1. Manual Testing Script (`api_workflow_test.sh`)

This script is designed for manual testing where human intervention is required during the email verification step.

### 2. CI/CD Testing Script (`api_workflow_ci_test.sh`)

This script is designed for automated CI/CD environments and does not require manual intervention. It directly updates the database to verify the user.

## Key Features

- **Unique Email Addresses**: Both scripts use randomly generated numbers (based on the current timestamp) to create unique email addresses for both test users and prospects, ensuring no conflicts between test runs.
- **Comprehensive Testing**: Tests the entire API workflow from user signup to email/call verification.
- **Detailed Logging**: Each step is logged with clear success/failure indicators.
- **Enhanced Error Handling**: Better error reporting and diagnostics for API call issues.
- **Verbose Mode**: Optional detailed logging for troubleshooting API communication problems.
- **Request Timeouts**: Configurable timeouts to prevent hanging on unresponsive API endpoints.

## Prerequisites

- Bash shell
- curl command-line tool
- Python 3.x
- Running ReachGenie backend instance
- PostgreSQL client (for CI/CD script)

## How to Run the Manual Test

1. Make the script executable:
   ```bash
   chmod +x api_workflow_test.sh
   ```

2. Run the test script:
   ```bash
   ./api_workflow_test.sh
   ```

   By default, the script connects to `http://localhost:8001`. To use a different API URL, set the `API_URL` environment variable:

   ```bash
   API_URL="https://your-api-url.com" ./api_workflow_test.sh
   ```

3. Enable verbose logging for more detailed output:
   ```bash
   VERBOSE=true ./api_workflow_test.sh
   ```

4. Adjust request timeout (default is 30 seconds):
   ```bash
   TIMEOUT=60 ./api_workflow_test.sh
   ```

## How to Run the CI/CD Test

1. Make the script executable:
   ```bash
   chmod +x api_workflow_ci_test.sh
   ```

2. Run the CI/CD test script with appropriate database connection variables:
   ```bash
   DB_HOST="localhost" DB_PORT="5432" DB_NAME="reachgenie" DB_USER="postgres" DB_PASSWORD="postgres" ./api_workflow_ci_test.sh
   ```

   You can also enable automatic cleanup of test data after the test completes:
   ```bash
   CLEANUP="true" ./api_workflow_ci_test.sh
   ```

## Debugging API Issues

If you encounter issues with API calls, you can troubleshoot by:

1. Enabling verbose mode:
   ```bash
   VERBOSE=true ./api_workflow_test.sh
   ```

2. Examining the detailed request and response information in the output

3. Checking the request headers and body data for formatting issues

4. Verifying that the API endpoint URLs are correct

5. Confirming that the API server is running and accessible

## Manual Intervention

The manual test script requires intervention at the email verification step since we can't programmatically click the verification link. During the test, you'll be asked to manually verify the user account. You can do this by:

1. Checking the application logs for the verification link
2. Manually running an SQL query to update the user's verification status
3. Using the development environment to directly verify the user

The CI/CD script automates this step by directly updating the database.

## Sample Files

- `sample_product.pdf.txt`: A sample text file used for product creation in the manual test
- The CI/CD script generates its own sample file dynamically

## Test Output

Both scripts provide detailed output for each step, indicating whether the operation was successful or not. If all steps are successful, you'll see a green checkmark (✓) next to each step.

## Troubleshooting

If a step fails, check:

1. Is the ReachGenie backend running and accessible?
2. Are the API endpoints working correctly?
3. Do you have the required permissions?
4. Is there an issue with the sample product file?
5. For the CI/CD script, are the database connection details correct?
6. Are there any special characters in the data that might be causing issues?
7. Are the request payloads formatted correctly?

For call and email testing, make sure your backend has the necessary integrations properly configured. 