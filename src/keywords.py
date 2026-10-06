"""Keyword baseline: the dumbest tagger that could work, to see what the LLM adds."""

KEYWORDS = {
    "late_delivery": ["late", "delay", "slow", "hour", "hrs", "mins", "minute", "wait", "on time",
                      "in time", "long time", "takes so long", "der se"],
    "missing_or_wrong_items": ["missing", "wrong item", "wrong product", "not delivered", "never delivered",
                               "didn't receive", "not received", "didn't get", "less quantity",
                               "marked delivered", "different product", "one item"],
    "quality_freshness": ["expired", "expiry", "stale", "rotten", "spoil", "damaged", "broken", "quality",
                          "fresh", "smell", "fungus", "leak", "torn", "dirty", "defective", "fake",
                          "duplicate", "ghatiya"],
    "fees_and_prices": ["charge", "fee", "price", "expensive", "costly", "cost", "coupon", "offer",
                        "discount", "free cash", "cashback", "surge", "tax", "sasta", "mehenga", "high"],
    "refunds_returns": ["refund", "return", "replace", "money back", "exchange", "reimburse"],
    "customer_support": ["support", "customer care", "customer service", "chat", "helpline", "complaint",
                         "bot", "no response", "agent", "email", "executive"],
    "app_payment_bugs": ["crash", "bug", "login", "otp", "payment", "upi", "glitch", "error", "not working",
                         "hang", "lag", "server", "update", "debited", "deducted", "location", "loading"],
    "out_of_stock": ["out of stock", "unavailable", "not available", "no stock", "unserviceable"],
    "no_complaint": ["good", "great", "nice", "best", "love", "excellent", "awesome", "fast", "happy",
                     "satisfied", "amazing", "perfect"],
}


def guess(text: str) -> str:
    """Driver with the most keyword hits. Praise words only count when nothing else hit."""
    text = text.lower()
    hits = {d: sum(k in text for k in words) for d, words in KEYWORDS.items()}
    complaints = {d: n for d, n in hits.items() if d != "no_complaint" and n}
    if complaints:
        return max(complaints, key=complaints.get)  # ties go to the earlier driver
    return "no_complaint" if hits["no_complaint"] else "other"


if __name__ == "__main__":
    assert guess("very high delivery charge") == "fees_and_prices"
    assert guess("they sent me an expired product") == "quality_freshness"
    assert guess("money deducted but order not placed") == "app_payment_bugs"
    assert guess("great app") == "no_complaint"
    assert guess("worst app ever") == "other"
    print("ok")
