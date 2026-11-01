def detect_priority(text, temperature=None):
    text = text.lower()

    critical_words = [
        "critical", "emergency", "fire",
        "danger", "life threatening",
        "system down"
    ]

    high_words = [
        "urgent", "immediately", "not working",
        "failure", "overheating", "serious",
        "broken"
    ]

    low_words = [
        "suggestion", "general inquiry",
        "information", "feedback"
    ]

    if temperature is not None:
        if temperature >= 70:
            return "Critical"
        elif temperature > 50:
            return "High"

    if any(word in text for word in critical_words):
        return "Critical"

    if any(word in text for word in high_words):
        return "High"

    if any(word in text for word in low_words):
        return "Low"

    return "Medium"