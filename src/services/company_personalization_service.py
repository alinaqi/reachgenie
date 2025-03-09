"""
Company personalization service for generating personalized content based on company information.
"""
import os
import logging
import json
from typing import Dict, List, Optional
import openai
from src.config import get_settings
from src.services.perplexity_service import perplexity_service

# Set up logger
logger = logging.getLogger(__name__)

settings = get_settings()

class CompanyPersonalizationService:
    def __init__(self):
        """Initialize the company personalization service with OpenAI client"""
        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
    
    async def get_company_info(self, company_name: str, website: Optional[str] = None) -> Dict:
        """
        Research company information using Perplexity API
        
        Args:
            company_name: Name of the company to research
            website: Optional company website URL
            
        Returns:
            Dict containing company information
        """
        try:
            # Try to get company information using Perplexity
            if website:
                company_info = await perplexity_service.fetch_company_info(website)
                if company_info:
                    return company_info
                
            # If no website or if fetch_company_info failed, try get_company_insights
            insights = await perplexity_service.get_company_insights(
                company_name=company_name,
                company_website=website,
                company_description=f"{company_name} company information"
            )
            
            if insights:
                return {
                    "brief_description": insights.get("description", f"{company_name} is a company."),
                    "key_products": insights.get("products_services", ""),
                    "industry": insights.get("industry", ""),
                    "target_audience": insights.get("target_audience", ""),
                    "company_size": insights.get("company_size", ""),
                    "founding_info": insights.get("founding_info", ""),
                    "unique_selling_points": insights.get("unique_selling_points", "")
                }
            
            # If all else fails, return minimal information
            return {
                "brief_description": f"{company_name} is a company.",
                "key_products": "",
                "industry": "",
                "target_audience": "",
                "company_size": "",
                "founding_info": "",
                "unique_selling_points": ""
            }
            
        except Exception as e:
            logger.error(f"Error getting company info: {str(e)}")
            logger.exception(e)
            
            # Return minimal information if there's an error
            return {
                "brief_description": f"{company_name} is a company.",
                "key_products": "",
                "industry": "",
                "target_audience": "",
                "company_size": "",
                "founding_info": "",
                "unique_selling_points": ""
            }
    
    async def generate_personalized_value_proposition(self, company_info: Dict) -> str:
        """
        Generate a personalized value proposition for the company using GPT-4o-mini
        
        Args:
            company_info: Dict containing company information
            
        Returns:
            str: Personalized value proposition
        """
        try:
            # Get marketing content from the guide
            marketing_content = self._get_marketing_content()
            
            # Create the system prompt for the model
            system_prompt = """You are a sales expert working for ReachGenie, an AI-powered sales development platform. 
            Your task is to create a personalized value proposition that explains how ReachGenie can help the specific company.
            
            Use the company information and ReachGenie's marketing content to create a compelling, concise value proposition.
            
            Your response should:
            1. Show understanding of the company's business
            2. Highlight how ReachGenie specifically addresses their needs
            3. Mention 2-3 relevant features that would benefit them most
            4. Be conversational and engaging
            5. Be concise (3-4 paragraphs maximum)
            6. Be written directly to the recipient in second person ("you", "your company")
            
            IMPORTANT: DO NOT begin your response with any greeting like "Hi there!", "Hello!" or similar phrases. The greeting will be added separately.
            Start your response directly with the first sentence of your value proposition.
            
            DO NOT:
            - Use generic marketing language that could apply to any company
            - Make specific claims about the company that aren't supported by the information
            - Write more than 4 paragraphs
            - Begin with a greeting phrase like "Hi" or "Hello"
            
            Format your response as clean HTML paragraphs.
            """
            
            # Create the user prompt with company info and marketing content
            user_prompt = f"""
            Company Information:
            - Company: {company_info.get('brief_description', '')}
            - Products/Services: {company_info.get('key_products', '')}
            - Industry: {company_info.get('industry', '')}
            - Target Audience: {company_info.get('target_audience', '')}
            - Company Size: {company_info.get('company_size', '')}
            - Unique Selling Points: {company_info.get('unique_selling_points', '')}
            
            ReachGenie Marketing Content:
            {marketing_content}
            
            Generate a personalized value proposition explaining how ReachGenie can help this specific company.
            """
            
            # Make the request to OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=700
            )
            
            # Extract the content
            content = response.choices[0].message.content
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating personalized value proposition: {str(e)}")
            logger.exception(e)
            
            # Return a generic value proposition if there's an error
            return """
            <p>ReachGenie is an AI-powered sales development platform that automates personalized outreach through email and voice channels while maintaining authentic human-like conversations. Our platform can help you scale your outreach efforts without sacrificing quality, turning cold leads into warm opportunities.</p>
            
            <p>With features like AI-powered email personalization, conversational email AI, and intelligent calendar management, ReachGenie can help you generate more meetings with less effort and increase your conversion rates.</p>
            """
    
    async def generate_engagement_tips(self, company_info: Dict) -> List[Dict[str, str]]:
        """
        Generate personalized customer engagement tips for the company using GPT-4o-mini
        
        Args:
            company_info: Dict containing company information
            
        Returns:
            List of tips, each with title and content
        """
        try:
            # Create the system prompt for the model
            system_prompt = """You are a sales and customer engagement expert. 
            Your task is to create three personalized tips for engaging customers based on the company's information.
            
            Your tips should:
            1. Be specific to the company's industry and business model
            2. Be actionable and implementable
            3. Be forward-looking and growth-oriented
            4. Each have a clear, concise title (5-8 words)
            5. Each have a detailed explanation (2-3 sentences minimum)
            
            Format each tip with:
            - A clear title
            - A detailed explanation
            
            DO NOT use numbering in your response. Each tip MUST have both a title and detailed content.
            """
            
            # Create the user prompt with company info
            industry = company_info.get('industry', 'your industry')
            user_prompt = f"""
            Company Information:
            - Description: {company_info.get('brief_description', '')}
            - Products/Services: {company_info.get('key_products', '')}
            - Industry: {industry}
            - Target Audience: {company_info.get('target_audience', '')}
            - Unique Selling Points: {company_info.get('unique_selling_points', '')}
            
            Generate 3 practical, personalized customer engagement tips for this company to help them convert more prospects.
            Structure your response as follows - each tip MUST have both a title and detailed content:
            
            Tip One Title
            Tip one detailed explanation (2-3 sentences minimum)
            
            Tip Two Title
            Tip two detailed explanation (2-3 sentences minimum)
            
            Tip Three Title
            Tip three detailed explanation (2-3 sentences minimum)
            """
            
            # Make the request to OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            # Extract the content
            content = response.choices[0].message.content
            logger.info(f"Raw engagement tips content: {content}")
            
            # Split into 3 tips by looking for double line breaks which typically separate the tips
            tips_raw = content.split("\n\n")
            tips_raw = [t for t in tips_raw if t.strip()]  # Remove empty items
            
            # Process each tip to extract title and content
            tips = []
            for i, tip_text in enumerate(tips_raw[:3]):  # Take up to 3 tips
                lines = tip_text.strip().split("\n")
                if len(lines) >= 2:  # Must have at least 2 lines (title and content)
                    title = lines[0].strip()
                    # Join all remaining lines as content
                    content = ' '.join([line.strip() for line in lines[1:] if line.strip()])
                    
                    # If content is too short, enhance it
                    if len(content) < 50:
                        content += f" This approach helps businesses in the {industry} industry connect with more potential clients and increase their conversion rates."
                    
                    tips.append({
                        "title": title,
                        "content": content
                    })
            
            # Ensure we have exactly 3 tips
            while len(tips) < 3:
                if len(tips) == 0:
                    tips.append({
                        "title": "Personalize Your Initial Outreach",
                        "content": f"Research your prospects before reaching out and reference specific details about their business in your communications. This shows that you've done your homework and are genuinely interested in their needs, not just making a sale."
                    })
                elif len(tips) == 1:
                    tips.append({
                        "title": "Focus on Value, Not Features",
                        "content": f"When engaging with prospects, emphasize the specific outcomes and ROI your solution provides rather than just listing features. This helps prospects understand exactly how your offering will solve their problems and deliver tangible results."
                    })
                else:
                    tips.append({
                        "title": "Implement a Multi-Channel Approach",
                        "content": f"Engage prospects across multiple touchpoints including email, phone, and social media. This creates more opportunities for connection and shows persistence without being pushy, significantly increasing your chances of getting a response."
                    })
            
            return tips[:3]
            
        except Exception as e:
            logger.error(f"Error generating engagement tips: {str(e)}")
            logger.exception(e)
            
            # Return generic tips as fallback
            industry = company_info.get('industry', 'your industry')
            return [
                {
                    "title": "Personalize Your Initial Outreach",
                    "content": f"Research your prospects before reaching out and reference specific details about their business in your communications. This shows that you've done your homework and are genuinely interested in their needs, not just making a sale."
                },
                {
                    "title": "Focus on Value, Not Features",
                    "content": f"When engaging with prospects, emphasize the specific outcomes and ROI your solution provides rather than just listing features. This helps prospects understand exactly how your offering will solve their problems and deliver tangible results."
                },
                {
                    "title": "Implement a Multi-Channel Approach",
                    "content": f"Engage prospects across multiple touchpoints including email, phone, and social media. This creates more opportunities for connection and shows persistence without being pushy, significantly increasing your chances of getting a response."
                }
            ]
    
    def _get_marketing_content(self) -> str:
        """Get relevant marketing content from the marketing guide"""
        return """
        ReachGenie is an AI-powered sales development platform that automates personalized outreach through email and voice channels while maintaining authentic human-like conversations. The platform empowers sales teams to scale their outreach efforts without sacrificing quality, turning cold leads into warm opportunities through intelligent, contextual engagement.

        Core Value Proposition:
        1. Creating authentic conversations - Not just sending emails and making calls, but engaging prospects in meaningful two-way communication
        2. Scaling human-quality outreach - Maintaining personalized, contextual communication at scale
        3. Increasing conversion rates - Generating more meetings and opportunities through intelligent follow-up and response management
        4. Saving time for sales teams - Automating routine outreach tasks while improving quality
        5. Learning and improving over time - Using AI to continuously refine messaging based on response data

        Key Features:
        1. Intelligent Outreach Campaigns - Create multi-touch, multi-channel campaigns in minutes
        2. AI-Powered Email Personalization - Generate highly personalized emails for each prospect automatically
        3. Conversational Email AI - Respond to prospect replies automatically with contextually relevant messages
        4. AI Voice Calling - Engage prospects with natural-sounding AI voice calls
        5. Intelligent Calendar Management - Automatically schedule meetings when prospects express interest
        6. Comprehensive Lead Management - Centralize all lead information in one unified database
        7. Ideal Customer Profile (ICP) Generation - Define your perfect customer with AI-powered ICP generation
        8. In-depth Analytics and Reporting - Track campaign performance in real-time

        What Makes ReachGenie Special:
        1. True Conversational AI - Creates authentic two-way conversations with prospects
        2. Multi-Channel Coordination - Integrates email and voice outreach in coordinated campaigns
        3. Deep Personalization - Researches each company and contact to generate truly personalized outreach
        4. Automated Meeting Booking - Detects meeting interest and automatically handles scheduling
        5. Self-Improving System - Learns from every interaction to continuously improve outreach effectiveness
        """ 