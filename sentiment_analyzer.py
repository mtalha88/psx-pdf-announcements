"""
Sentiment Analyzer - Keyword-based scoring for PSX announcements.
"""

KEYWORDS = [
    # Strong Positive (+25-40)
    ("debt free", 40, "Debt Free"),
    ("bonus issue", 30, "Bonus Issue"),
    ("special dividend", 30, "Special Dividend"),
    ("capacity expansion", 30, "Expansion"),
    ("record profit", 30, "Record Profit"),
    ("share buyback", 25, "Buyback"),
    ("final cash dividend", 25, "Final Dividend"),
    ("interim cash dividend", 20, "Interim Dividend"),
    ("contract awarded", 25, "Contract Win"),
    
    # Moderate Positive (+10-15)
    ("profit after tax", 15, "Profit"),
    ("earnings per share", 10, "EPS"),
    ("revenue growth", 10, "Revenue Growth"),
    ("profit increased", 15, "Profit Growth"),
    
    # Strong Negative (-25-40)
    ("delisting", -40, "Delisting Risk"),
    ("default", -40, "Default"),
    ("liquidation", -35, "Liquidation"),
    ("loss after tax", -25, "Loss"),
    ("plant shutdown", -30, "Shutdown"),
    
    # Moderate Negative (-10-15)
    ("loss per share", -20, "Loss Per Share"),
    ("profit decreased", -20, "Profit Decline"),
    ("delay", -10, "Delay"),
    ("decline", -10, "Decline"),
]

def analyze_sentiment(text: str) -> dict:
    """Analyze text sentiment using keyword matching."""
    if not text:
        return {"score": 0, "impact": "neutral", "signals": []}
    
    text = text.lower()
    score = 0
    signals = []
    
    for term, points, label in KEYWORDS:
        if term in text:
            score += points
            signals.append(label)
    
    # Determine impact level
    if score >= 30:
        impact = "strong_bullish"
    elif score >= 15:
        impact = "bullish"
    elif score <= -30:
        impact = "strong_bearish"
    elif score <= -15:
        impact = "bearish"
    else:
        impact = "neutral"
    
    return {
        "score": score,
        "impact": impact,
        "signals": signals[:5]  # Top 5 signals
    }

if __name__ == "__main__":
    # Test
    test_texts = [
        "Final Cash Dividend of Rs. 5 per share declared",
        "Company reports loss after tax of Rs. 100 million",
        "Board meeting scheduled for quarterly results"
    ]
    
    for t in test_texts:
        result = analyze_sentiment(t)
        print(f"{t[:40]}... -> {result['impact']} ({result['score']})")
