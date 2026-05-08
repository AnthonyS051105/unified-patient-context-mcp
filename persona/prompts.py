PERSONA_PROMPTS: dict[str, str] = {
    "physician": (
        "You are adapting clinical information for a physician. "
        "Use full medical terminology. Include clinical reasoning and differential considerations. "
        "Show all relevant data including raw values and trends. Be comprehensive and precise. "
        "Clinical data:\n{data}\n\nAdapt this for a physician (narrative format, no word limit):"
    ),
    "nurse": (
        "You are adapting clinical information for a bedside nurse. "
        "Use clear nursing language. Structure your response with three sections:\n"
        "WATCH: (specific values and thresholds to monitor)\n"
        "ESCALATE IF: (exact trigger values that require calling the physician)\n"
        "ACTION NOW: (immediate nursing interventions)\n"
        "Keep it under 300 words. Use bullet points. No complex diagnostic terminology.\n"
        "Clinical data:\n{data}\n\nAdapt this for a nurse:"
    ),
    "pharmacist": (
        "You are adapting clinical information for a clinical pharmacist. "
        "Focus on:\n"
        "- Drug interactions (severity: major/moderate/minor)\n"
        "- Renal dosing adjustments needed based on current labs\n"
        "- Contraindications based on current clinical status\n"
        "- Alternative medications if dose adjustment is needed\n"
        "Keep it under 400 words. Use structured format.\n"
        "Clinical data:\n{data}\n\nAdapt this for a pharmacist:"
    ),
    "patient": (
        "You are explaining clinical information to a patient. "
        "Rules:\n"
        "- Use 6th grade reading level (no medical jargon)\n"
        "- Start with a reassuring but honest opening\n"
        "- Explain WHAT is happening in simple terms\n"
        "- Tell them WHAT WILL HAPPEN NEXT\n"
        "- Suggest 2-3 QUESTIONS they can ask their doctor\n"
        "- Maximum 200 words\n"
        "Clinical data:\n{data}\n\nExplain this to a patient in plain language:"
    ),
}
