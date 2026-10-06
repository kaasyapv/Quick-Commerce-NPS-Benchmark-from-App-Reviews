"""The ten labels and their definitions. Same words as labelling_rules.md, which a check enforces."""
from pathlib import Path

DRIVERS = {
    "late_delivery": "order arrived late or took far longer than promised",
    "missing_or_wrong_items": "items missing, wrong or short in the order, or marked delivered but never arrived",
    "quality_freshness": "stale, expired, rotten, damaged or poor quality products",
    "fees_and_prices": "delivery, handling or platform fees, high prices, and coupons, offers or free cash that won't apply",
    "refunds_returns": "refund missing or slow, return or replacement refused",
    "customer_support": "support and rider behaviour: bots, no human agent, unhelpful or rude support, rude riders",
    "app_payment_bugs": "app and payment problems: crashes, OTP or login trouble, failed payments, money deducted, COD not offered, no cancel option",
    "out_of_stock": "items unavailable or out of stock, or not serviceable in my area",
    "other": "a complaint that fits none of the above",
    "no_complaint": "no complaint, or too vague to name any problem (praise, or just 'worst app')",
}

RULES = Path(__file__).resolve().parents[1] / "labelling_rules.md"


if __name__ == "__main__":
    text = RULES.read_text()
    for name, definition in DRIVERS.items():
        assert f"* {name}: {definition}\n" in text, f"{name} differs from labelling_rules.md"
    print("definitions match labelling_rules.md")
