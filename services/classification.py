def classify_ticket(text):
    text = text.lower()

    categories = {
        "Technical": [
            "error", "bug", "crash", "device",
            "software", "hardware", "not working",
            "technical", "network", "internet"
        ],

        "Billing": [
            "payment", "refund", "invoice",
            "billing", "charged", "transaction",
            "money", "price"
        ],

        "Account": [
            "login", "password", "account",
            "username", "signup", "sign in"
        ],

        "Delivery": [
            "delivery", "shipping", "order",
            "tracking", "package", "late"
        ],

        "Service": [
            "support", "service", "staff",
            "response", "customer care"
        ]
    }

    scores = {}

    for category, keywords in categories.items():
        scores[category] = sum(
            1 for word in keywords if word in text
        )

    best_category = max(scores, key=scores.get)

    if scores[best_category] == 0:
        return "General"

    return best_category