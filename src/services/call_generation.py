from src.config import get_settings
from openai import AsyncOpenAI
from src.database import get_product_by_id

import logging
logger = logging.getLogger(__name__)

async def generate_call_script(lead: dict, campaign: dict, company: dict, insights: str) -> str:
    """
    Generate personalized call script based on campaign and company insights using OpenAI.
    
    Args:
        lead: The lead information
        campaign: The campaign details
        company: The company information
        insights: Generated company insights
        
    Returns:
        A string containing the generated call script
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
            logger.info(f"Using enriched product information for call script generation")
            
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

        # Default agent name
        agent_name = "Alex"

        # If company has voice_agent_settings with a prompt, try to extract agent name
        if company.get('voice_agent_settings') and company['voice_agent_settings'].get('prompt'):
            # Ask OpenAI to extract the agent name from the prompt
            name_extraction_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI that extracts the sales agent's name from a prompt. Return ONLY the name, nothing else. If no name is found, return 'Alex'."
                    },
                    {
                        "role": "user",
                        "content": f"Extract the sales agent's name from this sentence: {company['voice_agent_settings']['prompt']}"
                    }
                ],
                temperature=0.0,
                max_tokens=100
            )
            
            extracted_name = name_extraction_response.choices[0].message.content.strip()
            if extracted_name and extracted_name != "Alex":
                agent_name = extracted_name
                logger.info(f"Extracted agent name from prompt: {agent_name}")
        
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
        - Company Name: {company.get('name')}.
        - Email: {company.get('account_email', '')}

        Generate a call script for the lead. For the call script, create an outbound sales conversation following this format:
        
        Your name is {agent_name}, and you're a sales agent working for {company.get('name')}. You are making an outbound call to a prospect/lead.

        The script should:
        - Start with: "Hello this is {agent_name}, I am calling on behalf of {company.get('name')}. Do you have a bit of time?"
        - Focus on understanding their current solution and pain points
        - Share relevant benefits based on their industry
        - Include natural back-and-forth dialogue with example prospect responses
        - Show how to handle common objections
        - End with clear next steps
        - Use the company insights and analysis to make the conversation specific to their business
        {f'''
        - Use the detailed product information to make your pitch more specific
        - Incorporate the key value propositions in your conversation
        - If appropriate, mention how the product compares to competitors
        - Use market insights to show industry knowledge
        - Reference positive reviews when useful to build credibility
        ''' if enriched_info else ""}

        Format the conversation as:
        {agent_name}: [what {agent_name} says]
        Prospect: [likely response]
        {agent_name}: [{agent_name}'s response]
        [etc.]

        Return the conversation in plain text format, with each line of dialogue on a new line.
        Do not include any JSON formatting or other markup.
        """

        #logger.info(f"Generated Prompt: {prompt}")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI that creates personalized sales content. Format the conversation as a plain text script with each line of dialogue on a new line."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Get the plain text response
        script = response.choices[0].message.content.strip()
        return script
        
    except Exception as e:
        logger.error(f"Failed to generate call script: {str(e)}")
        return None