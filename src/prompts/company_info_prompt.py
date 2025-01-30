COMPANY_INFO_PROMPT = """Given the company website {website}, please provide the following information in a structured format:

1. Company Overview: A brief summary of what the company does and its main value proposition.
2. Company Background/History: Key milestones, founding date, and significant events in the company's history.
3. Products and Services: A comprehensive list of the company's main offerings.
4. Address/Location: The company's headquarters or main office location.
5. Industry: The primary industry sector(s) the company operates in (e.g., IT, Tourism, Finance, Health, etc.).

Please provide the information in a JSON format with the following structure:
{
    "overview": "string",
    "background": "string",
    "products_services": "string",
    "address": "string",
    "industry": "string"
}

Focus on factual information available on the website and its subpages. If any information is not available, mark it as "Not available".""" 