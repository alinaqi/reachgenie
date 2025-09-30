import httpx
import json
import logging
from typing import Dict, Optional, List
from src.config import get_settings
import openai
from src.services.email_service import EmailService
from src.services.perplexity_service import perplexity_service
import re

# Set up logger
logger = logging.getLogger(__name__)

settings = get_settings()

class PartnerApplicationService:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.openai_api_key)
        self.email_service = EmailService()
    
    async def generate_confirmation_email(self, application_data: Dict) -> Dict:
        """
        Generate a personalized confirmation email using GPT-4o-mini and company research from Perplexity
        
        Args:
            application_data: Dict containing the partner application data
            
        Returns:
            Dict containing subject and body for the confirmation email
        """
        try:
            # First, get company information using Perplexity API
            company_info = await self._get_company_info(application_data)
            
            # Then, generate the personalized email with GPT-4o-mini
            email_content = await self._generate_personalized_email(application_data, company_info)
            
            return email_content
        except Exception as e:
            logger.error(f"Error generating confirmation email: {str(e)}")
            # Return a fallback template if there's an error
            return self._get_fallback_email(application_data)
    
    async def send_confirmation_email(self, application_data: Dict) -> bool:
        """
        Generate and send a personalized confirmation email for a partnership application
        
        Args:
            application_data: Dict containing the partner application data
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get personalized email content
            logger.info(f"Generating confirmation email for {application_data.get('contact_email')} from {application_data.get('company_name')}")
            email_content = await self.generate_confirmation_email(application_data)
            logger.info(f"Email content generated successfully with subject: {email_content['subject']}")
            
            # Send email using Mailjet service - with specific sender and CC
            await self.email_service.send_email(
                to_email=application_data.get('contact_email'),
                subject=email_content["subject"],
                html_content=email_content["body"],
                from_name="Qudsia Piracha",
                from_email="qudsia@workhub.ai",
                cc_email="ashaheen@workhub.ai"
            )
            
            logger.info(f"Sent confirmation email to {application_data.get('contact_email')} with CC to ashaheen@workhub.ai")
            return True
        except Exception as e:
            logger.error(f"Error sending confirmation email: {str(e)}")
            logger.exception(e)
            return False
    
    async def _get_company_info(self, application_data: Dict) -> Dict:
        """
        Get company information using the perplexity_service
        
        Args:
            application_data: Dict containing the partner application data
            
        Returns:
            Dict containing company information from Perplexity
        """
        company_name = application_data.get('company_name', '')
        company_website = application_data.get('website', '')
        company_description = application_data.get('motivation', '')
        
        try:
            # If website is provided, try to get detailed company info
            if company_website:
                logger.info(f"Fetching company info for {company_name} from website {company_website}")
                company_info = await perplexity_service.fetch_company_info(company_website)
                if company_info:
                    logger.info(f"Successfully fetched company info for {company_name}")
                    return company_info
            
            # If no website or fetch failed, try to get insights based on company name
            logger.info(f"Getting company insights for {company_name}")
            insights = await perplexity_service.get_company_insights(
                company_name=company_name,
                company_website=company_website,
                company_description=company_description
            )
            
            if insights:
                # Try to parse insights as JSON
                try:
                    start_idx = insights.find('{')
                    end_idx = insights.rfind('}') + 1
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = insights[start_idx:end_idx]
                        company_info = json.loads(json_str)
                        logger.info(f"Successfully parsed company insights for {company_name}")
                        return company_info
                except json.JSONDecodeError as e:
                    logger.warning(f"Could not parse JSON from insights: {e}")
                
                # If we couldn't parse JSON, create a dict with the raw insights
                logger.info(f"Returning unstructured insights for {company_name}")
                return {
                    "brief_description": insights,
                    "partnership_value": f"A partnership with {company_name} could help both companies expand their product offerings and reach new markets."
                }
            
            # If all else fails, return minimal information based on application data
            logger.warning(f"Could not get company information for {company_name} from Perplexity, using minimal data")
            return {
                "brief_description": f"{company_name} is a company in the {application_data.get('industry', 'technology')} industry.",
                "industry": application_data.get('industry', 'technology'),
                "key_products": "products and services",
                "company_size_estimate": application_data.get('company_size', 'unknown size'),
                "partnership_value": f"A partnership with {company_name} could help both companies expand their product offerings and reach new markets."
            }
                
        except Exception as e:
            logger.error(f"Error getting company info from Perplexity: {str(e)}")
            logger.exception(e)
            
            # Return minimal information based on application data
            return {
                "brief_description": f"{company_name} is a company in the {application_data.get('industry', 'technology')} industry.",
                "industry": application_data.get('industry', 'technology'),
                "partnership_value": f"A partnership with {company_name} could be beneficial for both organizations."
            }
    
    async def _generate_sales_tips(self, company_info: Dict, industry: str) -> List[Dict[str, str]]:
        """
        Generate personalized sales tips based on company information
        
        Args:
            company_info: Dict containing company information from Perplexity
            industry: Industry of the company
            
        Returns:
            List of 3 personalized sales tips as dictionaries with 'title' and 'content' keys
        """
        try:
            # Create the system prompt for the model
            system_prompt = """You are a sales and partnership expert tasked with providing actionable sales tips for a company.
            Based on the company information, generate 3 specific, practical sales expansion tips.
            
            Make the tips:
            1. Specific to their industry and business model
            2. Actionable and implementable
            3. Forward-looking and growth-oriented
            
            Format each tip with:
            - A clear, concise title (5-8 words)
            - A detailed explanation (2-3 sentences minimum)
            
            DO NOT use numbering in your response. The tips will be numbered during formatting.
            Each tip MUST have both a title and substantial explanation content.
            """
            
            # Create the user prompt with company info
            brief_description = company_info.get('brief_description', '')
            industry_info = company_info.get('industry', industry)
            key_products = company_info.get('key_products', '')
            
            user_prompt = f"""
            Company Information:
            - Description: {brief_description}
            - Industry: {industry_info}
            - Products/Services: {key_products}
            
            Generate 3 practical, personalized sales expansion tips for this company to help them grow their business.
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
            logger.info(f"Raw sales tips content: {content}")
            
            # Split into 3 tips by looking for double line breaks which typically separate the tips
            tips_raw = content.split("\n\n")
            tips_raw = [t for t in tips_raw if t.strip()]  # Remove empty items
            
            # Process each tip to extract title and content
            tips = []
            for i, tip_text in enumerate(tips_raw[:3]):  # Take up to 3 tips
                lines = tip_text.strip().split("\n")
                if len(lines) >= 2:  # Must have at least 2 lines (title and content)
                    title = lines[0].strip()
                    # Remove any numbering from the title
                    title = re.sub(r'^\d+\.\s*', '', title)
                    title = re.sub(r'^Tip\s+\d+[:.]\s*', '', title)
                    # Remove any markdown styling
                    title = re.sub(r'^#+\s*', '', title)
                    
                    # Join all remaining lines as content
                    content = ' '.join([line.strip() for line in lines[1:] if line.strip()])
                    
                    # If content is too short, enhance it
                    if len(content) < 50:
                        content += f" This approach helps businesses in the {industry} industry connect with more potential clients and increase their market reach."
                    
                    tips.append({
                        "title": title,
                        "content": content
                    })
                else:
                    # Handle case where the tip doesn't have both title and content
                    if i == 0:
                        tips.append({
                            "title": "Leverage Customer Success Stories",
                            "content": f"Collect and share detailed case studies showing how your products solve real problems. This builds credibility with prospects in the {industry} sector and provides tangible evidence of your value proposition."
                        })
                    elif i == 1:
                        tips.append({
                            "title": "Implement Strategic Partnerships",
                            "content": f"Form alliances with complementary service providers in the {industry} space to expand your reach. This creates win-win relationships that open new distribution channels and market opportunities."
                        })
                    else:
                        tips.append({
                            "title": "Invest in Industry-Specific Networking",
                            "content": f"Participate in targeted industry events and forums where your ideal clients gather. This positions your company as an active industry participant and creates valuable relationship-building opportunities."
                        })
            
            # Ensure we have exactly 3 tips
            while len(tips) < 3:
                if len(tips) == 0:
                    tips.append({
                        "title": "Leverage Customer Success Stories",
                        "content": f"Collect and share detailed case studies showing how your products solve real problems. This builds credibility with prospects in the {industry} sector and provides tangible evidence of your value proposition."
                    })
                elif len(tips) == 1:
                    tips.append({
                        "title": "Implement Strategic Partnerships",
                        "content": f"Form alliances with complementary service providers in the {industry} space to expand your reach. This creates win-win relationships that open new distribution channels and market opportunities."
                    })
                else:
                    tips.append({
                        "title": "Invest in Industry-Specific Networking",
                        "content": f"Participate in targeted industry events and forums where your ideal clients gather. This positions your company as an active industry participant and creates valuable relationship-building opportunities."
                    })
            
            return tips[:3]  # Return exactly 3 tips
            
        except Exception as e:
            logger.error(f"Error generating sales tips: {str(e)}")
            logger.exception(e)
            # Return generic tips as fallback
            return [
                {
                    "title": "Leverage Strategic Partnerships",
                    "content": f"Partner with complementary {industry} solution providers to expand your customer base. These alliances can open new markets and provide additional value to your existing clients."
                },
                {
                    "title": "Implement a Client Referral Program",
                    "content": "Incentivize existing clients to recommend your services for higher conversion rates. Referred leads typically close faster and have higher retention rates than cold prospects."
                },
                {
                    "title": "Focus on Vertical-Specific Marketing",
                    "content": "Target industries with the highest potential ROI through specialized campaigns. This focused approach allows you to tailor your messaging to specific pain points and industry terminology."
                }
            ]
    
    async def _generate_personalized_email(self, application_data: Dict, company_info: Dict) -> Dict:
        """
        Generate a personalized email using GPT-4o-mini
        
        Args:
            application_data: Dict containing the partner application data
            company_info: Dict containing company information from Perplexity
            
        Returns:
            Dict containing subject and body for the email
        """
        try:
            # Generate personalized sales tips
            sales_tips = await self._generate_sales_tips(
                company_info,
                application_data.get('industry', 'technology')
            )
            
            # Format the sales tips for inclusion in the email - with proper HTML structure
            formatted_tips = """
            <div class="tips-section">
                <h2>3 Tips to Expand Your Sales</h2>
            """
            
            for i, tip in enumerate(sales_tips):
                title = tip["title"]
                content = tip["content"]
                
                # Format with proper HTML
                formatted_tips += f"""
                <div class="tip">
                    <h3>{i+1}. {title}</h3>
                    <p>{content}</p>
                </div>
                """
            
            formatted_tips += "</div>"
            
            # Create the system prompt for the model
            system_prompt = """You are the ReachGenie partnership team. Your task is to write a personalized, warm, and professional confirmation email to a potential partner who has just applied to our partnership program.

            Use the company information provided from our research to show that we've done our homework. Make specific references to their business and how we might work together.

            The tone should be:
            1. Professional yet friendly
            2. Grateful for their interest
            3. Excited about potential collaboration
            4. Informative about next steps

            Include the following elements:
            1. A personalized greeting with their name
            2. Acknowledgment of their application
            3. A brief mention of what you know about their company (using our research)
            4. How their specific partnership type might work 
            5. Reference to the 3 sales tips we're providing
            6. Next steps in the process (review period of 3-5 business days)
            7. A professional signature block
            
            Format the response as clean, well-structured HTML with appropriate spacing, paragraphs, and formatting.
            Return a JSON object with 'subject' and 'body' fields.
            """
            
            # Create the user prompt with application data and company info
            user_prompt = f"""
            Partner Application Information:
            - Company: {application_data.get('company_name', 'your company')}
            - Contact Full Name: {application_data.get('contact_name', 'valued partner')}
            - Contact First Name: {application_data.get('contact_name', '').split()[0] if application_data.get('contact_name') else 'valued partner'}
            - Email: {application_data.get('contact_email', '')}
            - Partnership Type: {application_data.get('partnership_type', 'PARTNERSHIP')}
            - Company Size: {application_data.get('company_size', '')}
            - Industry: {application_data.get('industry', '')}
            - Motivation: {application_data.get('motivation', '')}
            
            Company Research Information:
            - Description: {company_info.get('brief_description', '')}
            - Products/Services: {company_info.get('key_products', '')}
            - Founded: {company_info.get('founding_info', '')}
            - Partnership Value: {company_info.get('partnership_value', '')}
            
            Sales Tips to Include (already formatted, include as-is):
            {formatted_tips}
            
            Signature to include at the end:
            Qudsia Piracha
            Director of Product
            ReachGenie 
            https://reachgenie.leanai.ventures
            
            IMPORTANT: Address the recipient by their first name only in the greeting, not their full name.
            
            Generate a personalized email confirmation as a JSON object with 'subject' and 'body' fields.
            The body should be properly formatted HTML with appropriate styling and spacing.
            """
            
            # Make the request to OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract the content
            content = response.choices[0].message.content
            email_data = json.loads(content)
            
            # Add CSS styling for better email formatting
            styled_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
                    h1 {{ color: #2c3e50; font-size: 24px; margin-top: 20px; }}
                    h2 {{ color: #3498db; font-size: 20px; margin-top: 15px; }}
                    h3 {{ color: #2980b9; font-size: 16px; margin-top: 15px; margin-bottom: 5px; }}
                    p {{ margin-bottom: 15px; }}
                    .tips-section {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0; }}
                    .tip {{ margin-bottom: 15px; }}
                    .tip h3 {{ margin-top: 5px; color: #2980b9; }}
                    .tip p {{ margin-top: 5px; margin-left: 10px; }}
                    .signature {{ margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; }}
                    .signature p {{ margin: 0; line-height: 1.4; }}
                    a {{ color: #3498db; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                {email_data.get("body", "")}
            </body>
            </html>
            """
            
            return {
                "subject": email_data.get("subject", "Thank you for your partnership application"),
                "body": styled_body
            }
        except Exception as e:
            logger.error(f"Error generating personalized email: {str(e)}")
            return self._get_fallback_email(application_data)
    
    def _get_fallback_email(self, application_data: Dict) -> Dict:
        """
        Get a fallback email template when personalization fails
        
        Args:
            application_data: Dict containing the partner application data
            
        Returns:
            Dict containing subject and body for the fallback email
        """
        # Extract first name from the full name
        full_name = application_data.get('contact_name', 'valued partner')
        first_name = full_name.split()[0] if full_name else 'valued partner'
        company_name = application_data.get('company_name', 'your company')
        
        subject = f"Thank you for your ReachGenie partnership application"
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
                h1 {{ color: #2c3e50; font-size: 24px; margin-top: 20px; }}
                h2 {{ color: #3498db; font-size: 20px; margin-top: 15px; }}
                h3 {{ color: #2980b9; font-size: 16px; margin-top: 15px; margin-bottom: 5px; }}
                p {{ margin-bottom: 15px; }}
                .tips-section {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0; }}
                .tip {{ margin-bottom: 15px; }}
                .tip h3 {{ margin-top: 5px; color: #2980b9; }}
                .tip p {{ margin-top: 5px; margin-left: 10px; }}
                .signature {{ margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; }}
                .signature p {{ margin: 0; line-height: 1.4; }}
                a {{ color: #3498db; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <p>Dear {first_name},</p>
            
            <p>Thank you for applying to the ReachGenie Partnership Program! We've received your application for {company_name} and are excited about the possibility of working together.</p>
            
            <p>Our team will review your application within the next 3-5 business days. Once the review is complete, we'll reach out with next steps.</p>
            
            <div class="tips-section">
                <h2>3 Tips to Expand Your Sales</h2>
                
                <div class="tip">
                    <h3>1. Leverage Strategic Partnerships</h3>
                    <p>Form alliances with complementary service providers to expand your reach and offer more comprehensive solutions to clients.</p>
                </div>
                
                <div class="tip">
                    <h3>2. Implement a Client Referral Program</h3>
                    <p>Create incentives for your existing clients to refer new business to you, as referred leads typically have higher conversion rates.</p>
                </div>
                
                <div class="tip">
                    <h3>3. Focus on Value-Based Selling</h3>
                    <p>Emphasize the specific ROI and business outcomes your solutions provide rather than just features and benefits.</p>
                </div>
            </div>
            
            <p>If you have any questions in the meantime, please don't hesitate to contact us at partnerships@reachgenie.ai.</p>
            
            <p>We look forward to exploring partnership opportunities with you!</p>
            
            <div class="signature">
                <p>Best regards,</p>
                <p>Qudsia Piracha</p>
                <p>Director of Product</p>
                <p>ReachGenie</p>
                <p><a href="https://reachgenie.leanai.ventures">https://reachgenie.leanai.ventures</a></p>
            </div>
        </body>
        </html>
        """
        
        return {
            "subject": subject,
            "body": body
        } 