COMPANY_INSIGHTS_PROMPT = """Analyze needs of our prospect who has the job title '{lead_title}' in the '{lead_department}' department in the company '{company_name}' with website '{company_website}'. Provide detailed insights in the following format:

BUSINESS OVERVIEW OF THE PROSPECT'S COMPANY {company_name}
[Review the company's business model, key products/services]

PROSPECT'S PROFESSIONAL INTERESTS
[Based on the lead's job title '{lead_title}' and department '{lead_department}', identify 3-5 specific professional interests they might have related to {company_name}'s products/services]

PAIN POINTS
[Identify and explain 3-5 key pain points someone in the position of '{lead_title}' in the '{lead_department}' department would likely face with their current products/services]

BUYING TRIGGERS
[Identify 3-5 specific events or conditions that would likely trigger this lead to make a purchasing decision for a new solution]

INDUSTRY CHALLENGES
[Discuss specific challenges in their industry and how they affect the business]


Please provide detailed insights for each section based on this context:
Lead job title: {lead_title}
Lead department: {lead_department}

Note: Provide comprehensive analysis in JSON format.

Important instructions:
1. Focus on factual information available on the website and its subpages
2. If lead title or department information is not provided, provide general insights for a typical decision-maker
3. Do not include any citations, references, or numbered annotations (like [1], [2], etc.) in the text
4. Provide clean, readable text without any reference markers"""