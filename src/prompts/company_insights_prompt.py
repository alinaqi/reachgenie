COMPANY_INSIGHTS_PROMPT = """Analyze {company_name} (website: {company_website}) and provide detailed insights in the following format:

CURRENT FUNCTIONALITY AND LIMITATIONS
[Analyze and describe their current functionality/features and any notable limitations]

CUSTOMER PAIN POINTS
[Identify and explain key pain points customers face with their current products/services]

INDUSTRY CHALLENGES
[Discuss specific challenges in their industry and how they affect the business]

REVENUE IMPACT ANALYSIS
[Analyze potential revenue impact of implementing improved solutions]

Please provide detailed insights for each section based on this context:
Company description: {company_description}

Note: Provide comprehensive analysis in plain text format, organized under these headings.

Important instructions:
1. Focus on factual information available on the website and its subpages
3. Do not include any citations, references, or numbered annotations (like [1], [2], etc.) in the text
4. Provide clean, readable text without any reference markers"""