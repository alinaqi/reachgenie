# Lead Enrichment Based on Product Value Proposition

This feature will enrich lead data based on the specific product/value proposition to create personalized outreach content.

## Implementation Todos

1. [ ] Create a new database table `lead_product_enrichment` with the following columns:
   - `id` (UUID, primary key)
   - `lead_id` (UUID, foreign key to leads table)
   - `product_id` (UUID, foreign key to products table)
   - `key_pain_points` (TEXT)
   - `value_gains` (TEXT)
   - `key_messages` (TEXT)
   - `created_at` (TIMESTAMP)
   - `updated_at` (TIMESTAMP)

2. [ ] Add database migration for the new table

3. [ ] Create database functions in `src/database.py`:
   - `create_lead_product_enrichment`
   - `get_lead_product_enrichment`
   - `update_lead_product_enrichment`

4. [ ] Create a background task function for lead enrichment:
   - Function: `enrich_lead_for_product(lead_id, product_id)`
   - This will run asynchronously when leads are associated with products

5. [ ] Implement Perplexity API integration to gather lead and company information:
   - Research lead's company and role
   - Find relevant industry trends
   - Identify potential challenges in their role/industry

6. [ ] Implement Anthropic API integration to generate enrichment content:
   - Generate key pain points based on lead information and product
   - Generate value gains the lead would experience from the product
   - Generate key messages that would resonate with the lead

7. [ ] Create an API endpoint to trigger enrichment:
   - `POST /api/companies/{company_id}/leads/{lead_id}/enrich`
   - This would accept a product_id and trigger the background task

8. [ ] Add functionality to automatically trigger enrichment when:
   - A new lead is added to the system
   - A new product is added to the company

9. [ ] Update the campaign execution process to use the enriched data:
   - Modify `generate_email_content` to incorporate enrichment data
   - Modify `generate_call_script` to incorporate enrichment data

10. [ ] Add endpoint to retrieve enrichment data:
    - `GET /api/companies/{company_id}/leads/{lead_id}/enrichment/{product_id}`

11. [ ] Create unit tests for the new functionality

12. [ ] Add documentation for lead enrichment feature:
    - Update API documentation
    - Update workflow documentation
    - Add examples of how enrichment improves personalization

## Technical Considerations

- Ensure proper error handling for API failures
- Implement caching for API responses to minimize costs
- Add rate limiting for enrichment requests
- Store raw API responses for debugging/auditing purposes
- Consider implementing a queue system for large-scale enrichment jobs 