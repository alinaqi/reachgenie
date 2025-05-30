"""
Progressive Reminder Strategies for 7-stage follow-up sequence
Each strategy includes tone, approach, psychological triggers, and CTAs
"""

REMINDER_STRATEGIES = {
    # First Reminder (1-3 days after initial email)
    None: {
        "name": "Gentle Check-In",
        "tone": "friendly and understanding",
        "approach": "acknowledge they're busy, softly reference original email",
        "psychological_trigger": "reciprocity and social proof",
        "opening_variations": [
            "I know how hectic {day_of_week}s can be",
            "Hope you're having a productive week",
            "Just floating this back to the top of your inbox",
            "I understand priorities shift quickly at {company}"
        ],
        "value_reinforcement": "brief reminder of the core benefit",
        "cta_options": [
            "Would a quick 10-minute call this week work?",
            "Is this still a priority for your team?",
            "Happy to send over a brief case study if helpful",
            "Should I circle back next quarter instead?"
        ],
        "signature_style": "warm",
        "ps_line": True,
        "ps_options": [
            "PS - I noticed {company} is {recent_company_event}. Congrats!",
            "PS - Quick thought: {relevant_insight}",
            "PS - {similar_company} saw {specific_result} with our solution"
        ]
    },
    
    # Second Reminder (4-7 days after initial)
    "r1": {
        "name": "Value Addition",
        "tone": "helpful and consultative",
        "approach": "share new insight, resource, or industry trend",
        "psychological_trigger": "authority and value-first",
        "opening_variations": [
            "Came across this {industry} report and thought of you",
            "Just saw {competitor} announced {relevant_news}",
            "Been thinking about your {department} challenges",
            "Quick update on what we discussed"
        ],
        "value_reinforcement": "new angle or additional benefit not mentioned before",
        "content_additions": [
            "relevant industry statistic",
            "brief case study snippet",
            "new feature announcement",
            "market trend affecting their business"
        ],
        "cta_options": [
            "Worth a brief exploration call?",
            "I have 2 slots open this week - interested?",
            "Should I send over our ROI calculator?",
            "Would your team benefit from a quick demo?"
        ],
        "signature_style": "professional",
        "attachment_suggestion": True
    },
    
    # Third Reminder (8-12 days after initial)
    "r2": {
        "name": "Social Proof & FOMO",
        "tone": "confident and peer-focused",
        "approach": "leverage competitor or peer success stories",
        "psychological_trigger": "social proof and fear of missing out",
        "opening_variations": [
            "3 other {industry} companies started with us this month",
            "{similar_company} just shared their results with us",
            "Your competitors are moving fast on this",
            "The {industry} landscape is shifting quickly"
        ],
        "value_reinforcement": "specific ROI or results from similar companies",
        "content_focus": "concrete examples and numbers",
        "cta_options": [
            "Want to see how {similar_company} achieved {result}?",
            "Shall I reserve a spot for you in our next cohort?",
            "Can I share what's working for companies like yours?",
            "15 minutes to show you the exact playbook?"
        ],
        "urgency_element": "subtle",
        "signature_style": "confident"
    },
    
    # Fourth Reminder (13-18 days after initial)
    "r3": {
        "name": "Problem Agitation",
        "tone": "direct but empathetic",
        "approach": "address the cost of inaction and growing problems",
        "psychological_trigger": "loss aversion and problem awareness",
        "opening_variations": [
            "Still seeing companies struggle with {pain_point}",
            "The cost of {problem} keeps growing",
            "Is {challenge} still slowing your team down?",
            "Most {job_title}s tell me {specific_challenge}"
        ],
        "value_reinforcement": "cost of not solving the problem",
        "content_focus": "problem implications and timeline",
        "questions_to_ask": [
            "What's your current approach to {problem}?",
            "How much time does your team waste on {task}?",
            "What would solving this mean for your {metric}?"
        ],
        "cta_options": [
            "Worth discussing even if the timing isn't perfect?",
            "Should we explore this before year-end?",
            "Can I show you a 5-minute solution overview?",
            "Is this problem big enough to warrant 20 minutes?"
        ],
        "signature_style": "understanding"
    },
    
    # Fifth Reminder (19-25 days after initial)
    "r4": {
        "name": "Alternative Approach",
        "tone": "creative and flexible",
        "approach": "offer different engagement options or formats",
        "psychological_trigger": "autonomy and convenience",
        "opening_variations": [
            "Different approach - would {alternative} work better?",
            "Instead of a call, what about {other_option}?",
            "I get it - calls are tough to schedule",
            "Let me try something different"
        ],
        "alternative_options": [
            "async video walkthrough",
            "email-based Q&A",
            "5-minute voice note exchange",
            "quick Slack/Teams chat",
            "1-page customized proposal",
            "self-guided trial with support"
        ],
        "value_reinforcement": "flexibility and respect for their time",
        "cta_options": [
            "Which format would work best for you?",
            "Should I just send over a custom video?",
            "Prefer to start with email questions?",
            "Want me to build a proposal async?"
        ],
        "signature_style": "flexible"
    },
    
    # Sixth Reminder (26-35 days after initial)
    "r5": {
        "name": "Last Value Drop",
        "tone": "generous and no-pressure",
        "approach": "share maximum value without expecting response",
        "psychological_trigger": "reciprocity and goodwill",
        "opening_variations": [
            "Whether we connect or not, thought this would help",
            "Free resource that might save you time",
            "Sharing this because it's too valuable not to",
            "No response needed - just wanted to help"
        ],
        "value_drops": [
            "exclusive industry report",
            "free tool or calculator",
            "insider tips document",
            "competitive analysis",
            "implementation checklist"
        ],
        "soft_cta": True,
        "cta_options": [
            "Hope this helps - here if you need anything",
            "Feel free to use this with your team",
            "Let me know if you want to discuss",
            "Always happy to chat if things change"
        ],
        "signature_style": "helpful"
    },
    
    # Seventh Reminder (36-45 days after initial)
    "r6": {
        "name": "Professional Breakup",
        "tone": "respectful and final",
        "approach": "acknowledge timing isn't right, leave door open",
        "psychological_trigger": "closure and future possibility",
        "opening_variations": [
            "Seems like this isn't the right time",
            "I'll stop reaching out after this",
            "Closing the loop on our conversation",
            "Last email from me on this"
        ],
        "acknowledgments": [
            "timing isn't always right",
            "priorities change",
            "you have a lot on your plate",
            "this might not be a current pain point"
        ],
        "future_door_opener": [
            "I'll check back in {timeframe}",
            "Feel free to reach out when ready",
            "I'll be here when the timing aligns",
            "Keeping you in our quarterly update list"
        ],
        "final_value": "one lasting insight or tip",
        "cta_options": [
            "Should I check back in 6 months?",
            "Mind if I send quarterly insights?",
            "Any feedback on our approach?",
            "Different person I should connect with?"
        ],
        "signature_style": "gracious",
        "unsubscribe_option": True
    }
}

def get_strategy(reminder_type: str) -> dict:
    """Get the strategy for a specific reminder type"""
    return REMINDER_STRATEGIES.get(reminder_type, REMINDER_STRATEGIES[None])

def get_strategy_progression() -> list:
    """Get the progression of reminder types in order"""
    return [None, "r1", "r2", "r3", "r4", "r5", "r6"]