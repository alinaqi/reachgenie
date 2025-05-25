from typing import Optional, Tuple
from src.services.perplexity_service import perplexity_service
from openai import AsyncOpenAI
from src.config import get_settings
from src.database import get_product_by_id
import json

import logging
logger = logging.getLogger(__name__)

async def get_or_generate_insights_for_lead(lead: dict, force_creation: bool = False):
    """
    Get or generate insights for a lead
    
    Args:
        lead: The lead information dictionary
        force_creation: If True, will regenerate insights even if they already exist
        
    Returns:
        Generated insights or None if generation fails
    """
    
    # Check if lead already has enriched data and we're not forcing regeneration
    insights = None
    if not force_creation and lead.get('enriched_data'):
        logger.info(f"Lead {lead['email']} already has enriched data, using existing insights")
        # We have enriched data, use it directly
        if isinstance(lead['enriched_data'], str):
            try:
                enriched_data = json.loads(lead['enriched_data'])
                insights = json.dumps(enriched_data)
            except json.JSONDecodeError:
                insights = lead['enriched_data']
        else:
            insights = json.dumps(lead['enriched_data'])
    
    # Generate company insights if we don't have any or if force_creation is True
    if force_creation or not insights:
        logger.info(f"{'Regenerating' if force_creation else 'Generating new'} insights for lead: {lead['email']}")
        insights = await generate_company_insights(lead, perplexity_service)
        
        # Save the insights to the lead's enriched_data if we generated new ones
        if insights:
            try:
                # Parse the insights JSON if it's a string
                enriched_data = {}
                if isinstance(insights, str):
                    # Try to extract JSON from the string response
                    insights_str = insights.strip()
                    # Check if the response is already in JSON format
                    try:
                        enriched_data = json.loads(insights_str)
                    except json.JSONDecodeError:
                        # If not, look for JSON within the string (common with LLM responses)
                        import re
                        json_match = re.search(r'```json\s*([\s\S]*?)\s*```|{[\s\S]*}', insights_str)
                        if json_match:
                            potential_json = json_match.group(1) if json_match.group(1) else json_match.group(0)
                            enriched_data = json.loads(potential_json)
                        else:
                            # If we can't extract structured JSON, store as raw text
                            enriched_data = {"raw_insights": insights_str}
                else:
                    enriched_data = insights
                
                # Update the lead with enriched data
                from src.database import update_lead_enrichment
                await update_lead_enrichment(lead['id'], enriched_data)
                logger.info(f"Updated lead {lead['email']} with new enriched data")
            except Exception as e:
                logger.error(f"Error storing insights for lead {lead['email']}: {str(e)}")
    
    if not insights:
        logger.error(f"Failed to generate insights for lead {lead['email']}")
        return None
    
    return insights


async def generate_company_insights(lead: dict, perplexity_service) -> dict:
    """Generate company insights using Perplexity API for a given lead"""
    try:
        company_name = lead.get('company', '')
        company_website = lead.get('website', '')
        company_description = lead.get('company_description', '')
        lead_title = lead.get('job_title', '')
        lead_department = lead.get('department', '')
        
        if not company_name and not company_website:
            logger.warning(f"Insufficient company data for lead {lead.get('id')}")
            return None
            
        insights = await perplexity_service.get_company_insights(
            company_name=company_name,
            company_website=company_website,
            company_description=company_description,
            lead_title=lead_title,
            lead_department=lead_department
        )
        
        if insights:
            logger.info(f"Generated insights for company: {company_name} for lead with title: {lead_title}")
        return insights
        
    except Exception as e:
        logger.error(f"Failed to generate company insights for lead {lead.get('id')}: {str(e)}")
        return None

async def generate_email_content(lead: dict, campaign: dict, company: dict, insights: str) -> Optional[tuple[str, str]]:
    """
    Generate personalized email content based on campaign and company insights using OpenAI.
    
    Args:
        lead: The lead information
        campaign: The campaign details
        company: The company information
        insights: Generated company insights
        
    Returns:
        Optional tuple of (subject, body) containing the generated email content, or None if generation fails
    """
    try:
        settings = get_settings()
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Get product details from database
        product = await get_product_by_id(campaign['product_id'])
        if not product:
            logger.error(f"Product not found for campaign: {campaign['id']}")
            return None
        
        # Prepare product information and check for enriched data
        product_info = product.get('description', 'Not available')
        enriched_info = product.get('enriched_information')
        enriched_data = ""
        
        if enriched_info:
            logger.info(f"Using enriched product information for email generation")
            
            if enriched_info.get('overview'):
                enriched_data += f"\nOverview: {enriched_info.get('overview')}"
            
            if enriched_info.get('key_value_proposition'):
                enriched_data += f"\nKey Value Proposition: {enriched_info.get('key_value_proposition')}"
            
            if enriched_info.get('pricing'):
                enriched_data += f"\nPricing: {enriched_info.get('pricing')}"
            
            if enriched_info.get('market_overview'):
                enriched_data += f"\nMarket Overview: {enriched_info.get('market_overview')}"
            
            if enriched_info.get('competitors'):
                enriched_data += f"\nCompetitors: {enriched_info.get('competitors')}"
            
            reviews = enriched_info.get('reviews', [])
            if reviews and len(reviews) > 0:
                enriched_data += "\nReviews:"
                for review in reviews:
                    enriched_data += f"\n- {review}"
        
        # Construct the prompt with lead and campaign information
        prompt = f"""
        You are an expert sales representative who have capabilities to pitch the leads about the product.

        Lead's history and Information:
        - Company Name: {lead.get('company', '')}
        - Contact Name: {lead.get('first_name', '')} {lead.get('last_name', '')}
        - Company Description: {lead.get('company_description', 'Not available')}
        - Analysis: {insights}

        Product Information:
        {product_info}
        
        {enriched_data if enriched_info else ""}

        Company Information (for signature):
        - Company URL: {company.get('website', '')}
        - Company Contact Person: {company.get('account_email').split('@')[0]}
        - Company Calendar Link: {company.get('custom_calendar_link', '')}

        Create two pieces of content:
        1. Email Subject: Compelling subject line mentioning our product and key benefits. Key guidelines for subject:
        - Keep it short (4-7 words, 40-60 characters)
        - Create curiosity without being clickbait
        - Include personalization when possible (name, company)
        - Align with the email content (don't mislead)
        - Use lowercase for a more personal feel, however first word of the subject should be uppercase
        - Avoid spam trigger words and excessive punctuation
        Examples:
        - "Intro from [mutual connection]"
        - "Your [specific detail] caught my attention"
        - "Quick idea for [specific pain point]"
        - "Question about [relevant topic]"
        - "Impressed by [something they did]"
        - "Following up on [recent event/news]"
        2. Email Content: Professional HTML email highlighting specific benefits for their business. Key guidelines for the email content: 
        - Personalization: Something that makes the email feel 1:1 and not mass-sent
        - Strong claim: A compelling statement about the value you provide
        - Evidence: Proof points that back up your claim
        - Clear next step: A specific action for the recipient to take
        - Brevity: Keep it under 200 words to respect their time

        Important Instructions for Email Content:
        - Use a professional tone
        - Focus on value proposition
        - Include a clear call to action to the landing page of the product
        - End with a professional signature using the company url and contact person as provided above
        - DO NOT use placeholders like 'Your Name' or 'Your Position'
        - Use the Company Contact Person and Company URL in the signature
        - Links should be formatted as <a href="link">link</a> instead of markdown format
        - Format the signature as:
          Best wishes,
          [Company Contact Person]
          [GIVE A NICE AND SHORT TITLE FOR THE CONTACT PERSON]
          [Company URL with utm_source=reachgenie]
          
          Signature Calendar Link Rule:
          IF company.get('custom_calendar_link') exists and is not empty THEN
          Add an empty line followed by:
          For appointment booking: [INSERT THE EXACT custom_calendar_link VALUE]
          END IF
        - IMPORTANT: In all urls, use utm_source=reachgenie
        {f'''
        - Use the detailed product information to craft a more compelling message
        - Incorporate the key value propositions that align with the lead's needs
        - If appropriate, highlight how the product stands out from competitors
        - Use market insights to show understanding of the lead's industry challenges
        - Reference positive reviews when useful to build credibility
        ''' if enriched_info else ""}

        Return the response in the following JSON format:
        {{
            "subject": "The email subject line",
            "body": "The HTML email content with proper signature"
        }}
        """

        #logger.info(f"Generated Prompt: {prompt}")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert sales representative crafting personalized email content. Always respond with valid JSON containing 'subject' and 'body' fields. Never use placeholder text in signatures."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={ "type": "json_object" }
        )
        
        # Parse the response
        content = response.choices[0].message.content.strip()
        email_content = json.loads(content)
        
        #logger.info(f"Generated email content for lead: {lead.get('email')}")
        return email_content["subject"].capitalize(), email_content["body"]
        
    except Exception as e:
        logger.error(f"Failed to generate email content: {str(e)}")
        return None