COMPANY_INSIGHTS_PROMPT = """
Analyze needs of our prospect who has the job title '{lead_title}' in the '{lead_department}' department in the company '{company_name}' with website '{company_website}'.
Based on the following company information, generate insights in the EXACT format specified below. Do not deviate from the structure or key names:

Company Name: {company_name}
Website: {company_website}
Description: {company_description}
Lead Title: {lead_title}
Lead Department: {lead_department}

businessModel: Review the company's business model
keyProductsServices: Review the company's key products/services
prospectProfessionalInterests: Based on the lead's job title '{lead_title}' and department '{lead_department}', identify 3-5 specific professional interests they might have related to {company_name}'s products/services
painPoints: Identify and explain 3-5 key pain points someone in the position of '{lead_title}' in the '{lead_department}' department would likely face with their current products/services
buyingTriggers: Identify 3-5 specific events or conditions that would likely trigger this lead to make a purchasing decision for a new solution
industryChallenges: Discuss specific challenges in their industry and how they affect the business

Required Format:
{{
  "businessOverview": {{
    "companyName": "<company name>",
    "businessModel": "<detailed 2-3 sentence description of how the company operates and generates revenue>",
    "keyProductsServices": [
      "<product/service 1>",
      "<product/service 2>",
      "<product/service 3>",
      "<product/service 4>"
    ]
  }},
  "prospectProfessionalInterests": [
    "<specific professional interest 1>",
    "<specific professional interest 2>",
    "<specific professional interest 3>",
    "<specific professional interest 4>",
    "<specific professional interest 5>"
  ],
  "painPoints": [
    "<specific pain point 1>",
    "<specific pain point 2>",
    "<specific pain point 3>",
    "<specific pain point 4>",
    "<specific pain point 5>"
  ],
  "buyingTriggers": [
    "<specific trigger 1>",
    "<specific trigger 2>",
    "<specific trigger 3>",
    "<specific trigger 4>",
    "<specific trigger 5>"
  ],
  "industryChallenges": [
    "<specific challenge 1>",
    "<specific challenge 2>",
    "<specific challenge 3>",
    "<specific challenge 4>",
    "<specific challenge 5>"
  ]
}}

IMPORTANT:
1. Use the EXACT key names shown
2. Format as valid JSON
3. Make all insights specific and relevant to the company's industry
4. Each array item should be a complete, meaningful phrase
5. Do not use placeholder text - provide real, relevant content
6. Focus on factual information available on the website and its subpages
7. If lead title or department information is not provided, provide general insights for a typical decision-maker
8. Do not include any citations, references, or numbered annotations (like [1], [2], etc.) in the text
9. Provide clean, readable text without any reference markers
"""