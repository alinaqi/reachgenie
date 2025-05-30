# Reminder Strategy Configuration for ReachGenie
# This file contains the progressive reminder strategies for 7-stage email follow-ups

REMINDER_STRATEGIES = {
    None: {  # First reminder
        "name": "Gentle Follow-up",
        "tone": "friendly and understanding",
        "approach": "acknowledge they might be busy, briefly reiterate main value proposition",
        "focus": "convenience and timing",
        "cta": "simple yes/no question or request for best time to connect",
        "urgency_level": "low",
        "personalization_depth": "medium"
    },
    "r1": {  # Second reminder
        "name": "Value Addition",
        "tone": "helpful and consultative",
        "approach": "share new insight, resource, or case study relevant to their industry",
        "focus": "educational value and expertise demonstration",
        "cta": "offer specific value exchange (free assessment, benchmark report, etc.)",
        "urgency_level": "low-medium",
        "personalization_depth": "high"
    },
    "r2": {  # Third reminder
        "name": "Social Proof",
        "tone": "confident and success-oriented",
        "approach": "share specific success story from similar company/role",
        "focus": "results and ROI demonstration",
        "cta": "propose specific meeting time with clear agenda",
        "urgency_level": "medium",
        "personalization_depth": "high"
    },
    "r3": {  # Fourth reminder
        "name": "Problem-Solution Fit",
        "tone": "direct and problem-solving focused",
        "approach": "address specific pain point based on their industry/role challenges",
        "focus": "specific problems we solve",
        "cta": "offer quick diagnostic call or problem-solving session",
        "urgency_level": "medium-high",
        "personalization_depth": "very high"
    },
    "r4": {  # Fifth reminder
        "name": "Urgency Creation",
        "tone": "professional with subtle urgency",
        "approach": "mention time-sensitive opportunity, limited availability, or market changes",
        "focus": "opportunity cost and competitive advantage",
        "cta": "specific deadline or limited-time offer",
        "urgency_level": "high",
        "personalization_depth": "medium"
    }
}
# Additional strategies (continued)
REMINDER_STRATEGIES["r5"] = {  # Sixth reminder
    "name": "Alternative Approach",
    "tone": "casual and peer-to-peer",
    "approach": "try different angle - maybe they're not the right person, ask for referral",
    "focus": "finding the right fit",
    "cta": "ask if someone else handles this or if priorities have changed",
    "urgency_level": "low",
    "personalization_depth": "low"
}

REMINDER_STRATEGIES["r6"] = {  # Seventh reminder
    "name": "Professional Break-up",
    "tone": "respectful and final",
    "approach": "acknowledge lack of response, provide easy opt-out, leave door open",
    "focus": "respect for their time and inbox",
    "cta": "final value offer with easy yes/no response option",
    "urgency_level": "none",
    "personalization_depth": "low"
}

# Subject line strategies for each reminder stage
SUBJECT_LINE_STRATEGIES = {
    None: {
        "prefix": "Re: ",
        "style": "standard follow-up"
    },
    "r1": {
        "prefix": "Quick question about ",
        "style": "curiosity-driven"
    },
    "r2": {
        "prefix": "",
        "style": "value-add",
        "template": "Saw this and thought of {company_name}"
    },
    "r3": {
        "prefix": "",
        "style": "urgency",
        "template": "Time-sensitive: {original_topic}"
    },
    "r4": {
        "prefix": "",
        "style": "peer-referral",
        "template": "{similar_company} just achieved {result}"
    },
    "r5": {
        "prefix": "Still interested? ",
        "style": "direct question"
    },
    "r6": {
        "prefix": "Last attempt - ",
        "style": "final notice"
    }
}