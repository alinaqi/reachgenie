# Campaign Summary Email

This document explains the Campaign Summary Email feature, which provides ReachGenie customers with a comprehensive overview of their campaign performance, enrichment results, and email management activities.

## Overview

The Campaign Summary Email provides a comprehensive report that goes beyond standard metrics to help users understand the effectiveness of their campaigns. It includes:

1. **Prospect Enrichment Information**
   - Examples of prospects who engaged with emails
   - Pain points and buying triggers identified through enrichment

2. **Automated Email Management**
   - Bounced emails that were automatically cleaned
   - Unsubscribe requests that were automatically processed

3. **Campaign Results**
   - Emails sent, opened, replied to
   - Meetings booked
   - Open rates, reply rates, etc.

4. **Industry Benchmark Comparison**
   - How the campaign is performing against B2B industry standards
   - Analysis of what the comparison means

5. **Next Steps Information**
   - Total prospects being processed
   - When reminder emails will be sent
   - Ongoing enrichment plans

## Using the Campaign Summary Feature

### Via API

The campaign summary email can be requested through the API:

```
POST /api/campaigns/{campaign_id}/summary-email
```

**Request body:**
```json
{
  "recipient_email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Campaign summary email sent to user@example.com"
}
```

### Via Command Line

For testing or manual generation, you can use the command-line script:

```bash
# Send the email
python -m src.scripts.generate_campaign_summary_email <campaign_id> <recipient_email>

# Save to file for testing
python -m src.scripts.test_campaign_summary <campaign_id> <recipient_email> --save-to-file
```

## Data Collection and Processing

The campaign summary aggregates data from multiple sources:

1. **Email Logs** - Track email opens, replies, and meetings booked
2. **Do Not Email List** - Track bounces and unsubscribes
3. **Lead Database** - Access enriched prospect information
4. **Campaign Metadata** - Campaign details and configuration
5. **Industry Benchmarks** - Compare performance against standards

## Customization Options

Future enhancements may include:

- Customizable email templates
- Additional metrics and insights
- Scheduled automatic summaries (weekly/monthly)
- PDF export option
- Integration with dashboards

## Implementation Details

### Database Functions

The feature relies on several database functions:

- `get_campaign_stats` - Retrieves comprehensive statistics for a campaign
- `get_engaged_prospects` - Retrieves prospects who have opened emails with their enrichment data
- `get_leads_by_campaign` - Retrieves all leads associated with a campaign

### Email Generation

The email is generated using:

- The base email template system
- HTML formatting for tables and styled sections
- Dynamic content based on campaign performance
- Conditional messaging based on benchmark comparisons

## Troubleshooting

Common issues:

1. **Missing data**: If the campaign is too new or has no data, the summary will show zeros for metrics
2. **Email not received**: Check spam folders and verify the recipient email address
3. **Error in generation**: Check the server logs for detailed error messages

## Example Output

The campaign summary email includes sections like:

```
Campaign Results Summary: [Campaign Name]

Dear [Company] Team,

We're excited to share the results of your ReachGenie campaign so far...

[Prospect Enrichment Section]
[Automated Email Management Section]
[Campaign Results Section with Metrics Table]
[Benchmark Comparison Section]
[Next Steps Section]

Thank you for using ReachGenie to power your outreach efforts.

Best regards,
The ReachGenie Team 