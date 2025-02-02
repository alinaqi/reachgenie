# API Endpoints Documentation

## Authentication Endpoints

### User Management
- `POST /api/auth/signup`
  - Create a new user account
  - Sends verification email
  - Returns: Account creation status

- `POST /api/auth/verify`
  - Verify user's email address
  - Requires: Verification token
  - Returns: Verification status

- `POST /api/auth/login`
  - Authenticate user
  - Returns: JWT access token

- `POST /api/auth/forgot-password`
  - Request password reset
  - Sends reset email
  - Returns: Reset request status

- `POST /api/auth/reset-password`
  - Reset user password
  - Requires: Reset token
  - Returns: Reset status

### User Profile
- `GET /api/users/me`
  - Get current user details
  - Requires: Authentication
  - Returns: User profile

- `PATCH /api/users/me`
  - Update user details
  - Requires: Authentication
  - Returns: Updated user profile

## Company Management

### Companies
- `POST /api/companies`
  - Create new company
  - Requires: Authentication
  - Returns: Company details

- `GET /api/companies`
  - List user's companies
  - Requires: Authentication
  - Returns: List of companies

- `GET /api/companies/{company_id}`
  - Get company details
  - Requires: Authentication
  - Returns: Company details

### Products
- `POST /api/companies/{company_id}/products`
  - Create new product
  - Requires: Authentication, File upload
  - Returns: Product details

- `GET /api/companies/{company_id}/products`
  - List company products
  - Requires: Authentication
  - Returns: List of products

- `PUT /api/companies/{company_id}/products/{product_id}`
  - Update product details
  - Requires: Authentication
  - Returns: Updated product

## Campaign Management

### Campaigns
- `POST /api/companies/{company_id}/campaigns`
  - Create new campaign
  - Requires: Authentication
  - Returns: Campaign details

- `GET /api/companies/{company_id}/campaigns`
  - List company campaigns
  - Optional: Filter by type (email/call)
  - Returns: List of campaigns

- `GET /api/campaigns/{campaign_id}`
  - Get campaign details
  - Requires: Authentication
  - Returns: Campaign details

- `POST /api/campaigns/{campaign_id}/run`
  - Start campaign execution
  - Requires: Authentication
  - Returns: Campaign status

### Email Management
- `GET /api/companies/{company_id}/emails`
  - List company email logs
  - Optional: Filter by campaign
  - Returns: List of email logs

- `POST /api/companies/{company_id}/account-credentials`
  - Update email account credentials
  - Requires: Authentication
  - Returns: Updated company details

## Lead Management

### Leads
- `POST /api/companies/{company_id}/leads/upload`
  - Upload leads from CSV
  - Returns: Task ID for tracking

- `GET /api/companies/{company_id}/leads`
  - List company leads
  - Returns: List of leads

- `GET /api/companies/{company_id}/leads/{lead_id}`
  - Get lead details
  - Returns: Lead details

## Call Management

### Calls
- `POST /api/companies/{company_id}/calls/start`
  - Start new call
  - Returns: Call details

- `GET /api/companies/{company_id}/calls`
  - List company calls
  - Optional: Filter by campaign
  - Returns: List of calls

- `GET /api/calls/{call_id}`
  - Get call details
  - Returns: Call details

## Task Management

### Tasks
- `GET /api/tasks/{task_id}`
  - Get task status
  - Returns: Task status and details

## Calendar Integration

### Cronofy
- `GET /api/companies/{company_id}/cronofy-auth`
  - Handle Cronofy OAuth callback
  - Returns: Authorization status

- `DELETE /api/companies/{company_id}/calendar`
  - Disconnect calendar integration
  - Returns: Disconnection status

## AI Integration

### Content Generation
- `POST /api/generate-campaign`
  - Generate campaign content
  - Requires: Achievement text
  - Returns: Generated campaign content 