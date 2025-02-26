# Campaign Workflows

This document details the end-to-end workflows for creating and running email and phone campaigns in the system, from company setup to campaign execution.

## End-to-End Campaign Workflow

### 1. Company Creation

1. **Create Company**:
   - Endpoint: `POST /api/companies`
   - User must be authenticated (JWT token required)
   - Required data: Company name (optionally website, industry, address)
   - If website is provided, the system fetches additional company information using Perplexity service
   - The system creates a user-company profile with admin role for the creator
   - Each company is stored in the `companies` table with a unique UUID

2. **Company Settings**:
   - For email campaigns, the company needs to have email credentials configured:
     - Account email
     - Account password (encrypted in database)
     - Account type (email provider)
   - For calendar functionality (appointment booking), Cronofy integration is available

### 2. Product Creation

1. **Create Product**:
   - Endpoint: `POST /api/companies/{company_id}/products`
   - Supports the following fields:
     - `product_name` (required): Name of the product
     - `description` (optional): Detailed description of the product
     - `product_url` (optional): URL to the product's website
     - `file` (optional): Documentation file for the product (.docx, .pdf, .txt)
   - When a product URL is provided, the system automatically enriches the product with additional information using Perplexity API
   - Files are stored in Supabase storage under "product-files" bucket
   - Product data is stored in the `products` table with references to company
   - The enriched information includes:
     - Overview: General description of the product
     - Key Value Proposition: Main selling points
     - Pricing: Pricing information if available
     - Reviews: Up to 3 good reviews
     - Market Overview: Information about the market
     - Competitors: List of competitors

2. **Product Enrichment Process**:
   - Triggered automatically when a product URL is provided
   - The system makes a request to the Perplexity API with company name and product URL
   - Perplexity API extracts detailed information about the product
   - This enriched information is stored in the `enriched_information` JSON field of the product
   - The enrichment happens during product creation or update

3. **Ideal Customer Profile (ICP) Generation**:
   - After creating a product, users can generate atomic ICPs for targeted outreach
   - Endpoint: `POST /api/companies/{company_id}/products/{product_id}/icp`
   - Accepts an optional `icp_input` parameter that allows users to provide specific instructions for ICP generation
   - The system uses the Anthropic Claude AI to analyze product information and generate at least 3 distinct ICPs
   - Each ICP is atomic, focusing on a single specific customer type (e.g., "VP of Sales at US Enterprise Software Companies")
   - ICPs include detailed information about:
     - Company attributes (industry, size, geography, maturity, funding)
     - Contact attributes (job titles, departments, seniority, responsibilities)
     - Business challenges that the product can solve
     - Buying triggers that would motivate purchase
     - Exclusion criteria for non-ideal customers
   - ICPs are stored as JSON in the product's database record

4. **ICP Management**:
   - ICPs can be retrieved using `GET /api/companies/{company_id}/products/{product_id}/icp`
   - Individual ICPs can be deleted using `DELETE /api/companies/{company_id}/products/{product_id}/icp/{icp_id}`
   - All ICPs for a product can be deleted using `DELETE /api/companies/{company_id}/products/{product_id}/icp`
   - ICPs can be regenerated any time using the POST endpoint
   - Having clear, atomic ICPs helps improve targeting for email and call campaigns

5. **Product Management**:
   - Products can be updated using `PUT /api/companies/{company_id}/products/{product_id}`
   - Products can be listed using `GET /api/companies/{company_id}/products`
   - Products can be deleted using `DELETE /api/companies/{company_id}/products/{product_id}`
   - Products belong to a specific company (one-to-many relationship)
   - When updating a product, enrichment will be re-triggered if the product URL is provided or changed

6. **Product Deletion**:
   - Endpoint: `DELETE /api/companies/{company_id}/products/{product_id}`
   - This is a soft delete operation - the product is marked as deleted but data is preserved
   - Requires authentication and proper company access permission
   - When a product is deleted:
     - It will no longer appear in product listings by default
     - Existing campaigns using this product remain functional
     - Historical data for the product is preserved for reporting
     - The product cannot be used for new campaigns
   - Note: There is no hard delete functionality to ensure data integrity for reporting

### 4. Lead Upload and Management

1. **Upload Leads**:
   - Endpoint: `POST /api/companies/{company_id}/leads/upload`
   - CSV file upload with lead data
   - Processing happens asynchronously via background task
   - The system creates a task record to track processing status
   - CSV file is stored in Supabase storage under "leads-uploads" bucket

2. **Lead Processing**:
   - Background task `process_leads_upload` processes the CSV file
   - Maps CSV headers to lead fields using OpenAI if needed
   - Creates lead records in database with company_id
   - Handles special fields like location moves, job changes
   - Leads are stored in the `leads` table with reference to company

3. **Lead Management**:
   - Leads can be retrieved using `GET /api/companies/{company_id}/leads`
   - Individual leads can be viewed using `GET /api/companies/{company_id}/leads/{lead_id}`
   - Leads are linked to companies, not individual products (important distinction)

4. **Lead Enrichment** (Coming Soon):
   - Leads will be enriched with personalized insights based on specific products
   - System will analyze lead information and product value proposition
   - For each lead-product combination, the system will generate:
     - Key pain points specific to the lead
     - Potential value gains for the lead from using the product
     - Key messages that would resonate with the lead
   - This enriched data will be used to improve personalization in both email and call campaigns

### 5. Campaign Creation

1. **Create Campaign**:
   - Endpoint: `POST /api/companies/{company_id}/campaigns`
   - Required data: name, type (email/call), product_id
   - Campaign types: "email" or "call"
   - Email campaigns may include a template message
   - Call campaigns may include a base script
   - Campaigns are stored in the `campaigns` table with references to:
     - company_id: Which company owns the campaign
     - product_id: Which product the campaign is promoting
   - The system leverages enriched product data to create more effective messaging when available
   - Product ICPs can guide targeting strategies and message customization

2. **Campaign Management**:
   - Campaigns can be retrieved using `GET /api/companies/{company_id}/campaigns`
   - Campaigns link products, company, and type of outreach together
   - Enriched product data (overview, value proposition, etc.) is used to enhance campaign personalization
   - ICPs help focus campaigns on specific customer segments with tailored messaging

### 6. Running Email Campaigns

1. **Initiate Campaign**:
   - Endpoint: `POST /api/campaigns/{campaign_id}/run`
   - Validates company credentials for email sending
   - Adds task to background process

2. **Email Campaign Execution Process** (`run_email_campaign`):
   - Gets leads with email addresses from the company
   - For each lead:
     - Generates company insights using Perplexity service
     - Uses enriched product data when available for email content generation
     - Leverages product enrichment to understand product features, value propositions, and market positioning
     - Generates personalized email content (subject, body) using insights and enriched product data
     - Creates email log record in database
     - Adds tracking pixel to email for open tracking
     - Sends email via SMTP using company credentials
     - Creates detailed email log record

3. **Email Tracking**:
   - System tracks email opens via tracking pixel
   - Has functionality to process email replies
   - Email logs are stored in `email_logs` and `email_log_details` tables

### 7. Running Phone Campaigns

1. **Initiate Campaign**:
   - Same endpoint: `POST /api/campaigns/{campaign_id}/run`
   - System detects campaign type and handles accordingly

2. **Phone Campaign Execution Process** (`run_call_campaign`):
   - Gets leads with phone numbers from the company
   - For each lead:
     - Generates company insights using Perplexity service
     - Uses enriched product data when available for call script generation
     - Leverages product enrichment data for detailed product features, value proposition, and competitive advantages
     - Generates personalized call script using OpenAI with both company insights and product enrichment data
     - Creates call record in database
     - Initiates call using Bland AI service with generated script
     - Updates call record with Bland call ID and details

3. **Call Handling**:
   - Bland AI handles the actual call using AI voice agent
   - System can book appointments based on call outcomes
   - Call logs, transcripts, and summaries are stored in the `calls` table

## Key Relationships and Data Flow

- **Company → Products**: One-to-many (a company can have multiple products)
- **Products → Enriched Information**: One-to-one (a product can be enriched with additional information from Perplexity API)
- **Company → Leads**: One-to-many (leads belong to a company, not specific products)
- **Company → Campaigns**: One-to-many (company owns multiple campaigns)
- **Product → Campaigns**: One-to-many (a product can be promoted in multiple campaigns)
- **Campaigns → Calls/Emails**: One-to-many (a campaign generates multiple communications)
- **Lead → Calls/Emails**: One-to-many (a lead can receive multiple communications)

## Important Insights

1. **Lead-Company Relationship**: Leads are associated with companies, not individual products. This allows targeting the same lead with different products.

2. **Campaign Structure**: Campaigns connect products with communication methods. Each campaign focuses on one product but can target many leads.

3. **Product Enrichment**: Products can be automatically enriched with detailed information when a product URL is provided. This enriched data is used to enhance the quality of campaigns and personalization, leading to more effective outreach.

4. **Ideal Customer Profiles**: The system generates atomic ICPs for each product, which help in:
   - Identifying the most promising leads for targeting
   - Tailoring messaging to specific customer segments
   - Improving campaign effectiveness through better targeting
   - Creating more personalized outreach content that addresses specific customer needs
   - Guiding lead qualification and prioritization

5. **Personalization Pipeline**: Both email and call campaigns use a similar personalization pipeline:
   - Company insights generation
   - Content generation (email body or call script)
   - Metadata tracking
   - Integration of product enrichment data to improve personalization
   - Alignment with ICPs for better targeting and messaging

6. **Background Processing**: Campaign execution happens asynchronously to prevent blocking API requests. 