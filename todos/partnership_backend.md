# ReachGenie Partnership Program - Backend Requirements

This document outlines the technical requirements for implementing the backend services to support ReachGenie's partnership program.

## 1. Data Model Requirements

### Partner Application Model

```typescript
PartnerApplication {
  id: UUID
  companyName: String (required)
  contactName: String (required)
  contactEmail: String (required)
  contactPhone: String (optional)
  website: String (optional)
  partnershipType: Enum["RESELLER", "REFERRAL", "TECHNOLOGY"] (required)
  companySize: Enum["1-10", "11-50", "51-200", "201-500", "501+"] (required)
  industry: String (required)
  currentSolutions: String (optional)
  targetMarket: String (optional)
  motivation: String (required)
  additionalInformation: String (optional)
  status: Enum["PENDING", "REVIEWING", "APPROVED", "REJECTED"] (default: "PENDING")
  createdAt: DateTime
  updatedAt: DateTime
}
```

### Partner Application Note Model (for internal use)

```typescript
PartnerApplicationNote {
  id: UUID
  applicationId: UUID (foreign key to PartnerApplication)
  authorName: String (required)
  note: String (required)
  createdAt: DateTime
}
```

## 2. API Endpoint Requirements

### Public Endpoints

#### Submit Partner Application
- **Endpoint**: `POST /api/partner-applications`
- **Description**: Allows potential partners to submit their application
- **Request Body**: Partner application data (except status, createdAt, updatedAt)
- **Response**: 
  - Success (201): Application ID and confirmation
  - Error (400): Validation errors
  - Error (500): Server error

### Protected Endpoints (Admin Only)

#### List Partner Applications
- **Endpoint**: `GET /api/admin/partner-applications`
- **Description**: Retrieve a list of partner applications with filtering and pagination
- **Query Parameters**: 
  - `status`: Filter by status
  - `partnershipType`: Filter by partnership type
  - `page`: Page number
  - `limit`: Number of items per page
  - `sortBy`: Field to sort by
  - `sortOrder`: "asc" or "desc"
- **Response**: List of applications with pagination metadata

#### Get Partner Application Details
- **Endpoint**: `GET /api/admin/partner-applications/{id}`
- **Description**: Get detailed information about a specific application
- **Response**: Complete application data including notes

#### Update Partner Application Status
- **Endpoint**: `PATCH /api/admin/partner-applications/{id}/status`
- **Description**: Update the status of a partner application
- **Request Body**: `{ status: "PENDING" | "REVIEWING" | "APPROVED" | "REJECTED" }`
- **Response**: Updated application

#### Add Note to Partner Application
- **Endpoint**: `POST /api/admin/partner-applications/{id}/notes`
- **Description**: Add an internal note to a partner application
- **Request Body**: `{ authorName: string, note: string }`
- **Response**: Created note data

#### Get Application Statistics
- **Endpoint**: `GET /api/admin/partner-applications/statistics`
- **Description**: Get statistics about partner applications (counts by status, type, etc.)
- **Response**: Statistics object

## 3. Notification Requirements

### Email Notifications

#### Application Received Confirmation
- **Trigger**: When a new partner application is submitted
- **Recipient**: Partner's contact email
- **Content**: Confirmation of application receipt, expected timeline, next steps

#### Application Status Change
- **Trigger**: When an application status changes
- **Recipient**: Partner's contact email
- **Content**: Information about the new status and next steps if applicable

#### Internal Notification
- **Trigger**: When a new partner application is submitted
- **Recipient**: Admin team email(s)
- **Content**: Summary of the new application with a link to view details

## 4. Security Requirements

- Authentication for admin endpoints using JWT or similar
- Rate limiting for public submission endpoint to prevent abuse
- Data validation for all inputs
- CORS configuration to allow only approved origins
- Secure storage of sensitive partner information

## 5. Integration Requirements

- Connect with the existing user system if approved partners need accounts
- Email service integration for notifications
- Optional CRM integration to track partner relationships
- Optional document storage for partnership agreements

## 6. Implementation Considerations

### Database
- PostgreSQL or similar relational database is recommended due to the structured nature of the data
- Add proper indexing for fields commonly used in queries (partnershipType, status, createdAt)

### API Implementation
- Use FastAPI or similar framework for building the REST API
- Implement proper error handling and logging
- Add pagination for list endpoints to handle large datasets
- Include proper data validation using Pydantic models

### Security
- Implement proper authentication middleware for protected endpoints
- Add validation to prevent common web attacks (XSS, CSRF, etc.)
- Implement proper logging for security events

## 7. Deployment and Operations

- Environment-specific configurations for development, staging, and production
- Automated tests for critical functionality
- Monitoring for API performance and errors
- Regular backups of application data

## 8. Partner Dashboard (Future Enhancement)

For a future phase, consider implementing a partner dashboard where approved partners can:

- View their application status
- Update their company information
- Access marketing materials
- Track referrals and commissions
- Register new deals
- Access training and certification materials

## 9. Partner Tiers (Future Enhancement)

Consider implementing a tier-based partner program with different benefits:

### Silver Partners
- Basic referral commissions
- Access to standard marketing materials
- Basic training resources

### Gold Partners
- Higher commission rates
- Co-marketing opportunities
- Dedicated partner manager
- Advanced training and certification

### Platinum Partners
- Premium commission structure
- Strategic business planning
- Joint marketing events
- Early access to new features

## 10. Implementation Phases

### Phase 1: Core Application System
- Implement partner application submission
- Create admin interface for application review
- Set up basic email notifications

### Phase 2: Enhanced Management
- Implement detailed analytics
- Add CRM integration
- Expand notification system

### Phase 3: Partner Portal
- Build partner dashboard
- Implement tier-based system
- Add training and resource center

## 11. Success Metrics

- Number of partner applications
- Application approval rate
- Partner-generated revenue
- Partner satisfaction score
- Partner program ROI 