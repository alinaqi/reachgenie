# ReachGenie Partnership Program - Application Flow

This document outlines the complete flow of the partnership application process, from initial submission to internal processing.

## Partner Application Submission Flow

### 1. Initial Request
When a potential partner submits an application through the frontend, it sends a POST request to:
```
POST /api/partner-applications
```

The request body includes fields like company name, contact information, partnership type, motivation, etc.

### 2. Data Validation
The submitted data is automatically validated against the `PartnerApplicationCreate` Pydantic model:
- Required fields (company_name, contact_name, email, etc.) are checked
- Data types are validated (email format, proper enums for partnership type)
- Any validation rules defined are enforced

If validation fails, a 422 Unprocessable Entity response is returned with details about the validation errors.

### 3. Database Storage
If validation passes, the application data is stored in the database:
```python
application_data = await create_partner_application(
    company_name=application.company_name,
    contact_name=application.contact_name,
    # ... other fields ...
)
```

This function inserts a new record into the `partner_applications` table with:
- All the provided application data
- A generated UUID as the ID
- The default status "PENDING"
- Current timestamp for created_at and updated_at

### 4. Personalized Email Generation (AI-Powered)
After storing the application, the system generates a personalized confirmation email using:

a) **Company Research** - Our system researches the company using Perplexity API:
```python
company_info = await partner_service._get_company_info(application_data)
```
The Perplexity API researches:
- What the company does
- Their products/services
- Company information
- Potential partnership value

b) **Personalized Email Generation** - Using GPT-4o-mini:
```python
email_content = await partner_service._generate_personalized_email(application_data, company_info)
```
The AI generates a personalized email that:
- Uses the contact's name
- References their company specifically
- Mentions their specific partnership type
- Includes researched details about their business
- Provides clear next steps

### 5. Email Sending
The system then sends the personalized email to the applicant:
```python
await smtp_client.send_email(
    to_email=application.contact_email,
    subject=email_content["subject"],
    html_content=email_content["body"],
    from_name="ReachGenie Partnerships"
)
```

### 6. Response
Finally, the endpoint returns a 201 Created response with:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Your partnership application has been submitted successfully. We will contact you soon."
}
```

### 7. Admin Review (Later)
After submission, administrators can:
- See the new application in the admin list (GET `/api/admin/partner-applications`)
- Review the detailed application (GET `/api/admin/partner-applications/{id}`)
- Add internal notes (POST `/api/admin/partner-applications/{id}/notes`)
- Update the application status (PATCH `/api/admin/partner-applications/{id}/status`)

All of these admin endpoints are protected with authentication and require a valid JWT token.

## Key Features of this System

- **Personalized experience**: Each application gets a customized response
- **AI-powered research**: Automatically researches the company to provide context
- **Secure admin access**: Protected endpoints for administrative functions
- **Complete tracking**: All applications are stored with their history and status
- **Scalable design**: Can handle many applications with proper pagination and filtering

## Technical Implementation Details

### Database Schema
The system uses two primary tables:
- `partner_applications` - Stores the main application data
- `partner_application_notes` - Stores internal notes about applications

### API Endpoints

#### Public Endpoints
- `POST /api/partner-applications` - Submit a new application

#### Admin Endpoints
- `GET /api/admin/partner-applications` - List applications with filtering and pagination
- `GET /api/admin/partner-applications/{id}` - Get detailed application information
- `PATCH /api/admin/partner-applications/{id}/status` - Update application status
- `POST /api/admin/partner-applications/{id}/notes` - Add internal notes
- `GET /api/admin/partner-applications/statistics` - Get application statistics

### Notification System
- Automatic email confirmation to the applicant
- Personalized content based on their application details
- Recognition of their company and business context

### Security Considerations
- All admin endpoints require authentication
- Input validation on all endpoints
- Database operations are properly secured 