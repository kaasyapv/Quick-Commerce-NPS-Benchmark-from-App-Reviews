"""The ten labels, each with the one line definition that taggers and the labelling page use."""

DRIVERS = {
    "late_delivery": "order arrived late or took far longer than promised",
    "missing_or_wrong_items": "items missing from the order, wrong item or wrong quantity",
    "quality_freshness": "stale, expired, rotten, damaged or poor quality products",
    "fees_and_prices": "delivery, handling or platform fees, surge charges, high prices, coupons not working",
    "refunds_returns": "refund missing or slow, return or replacement refused",
    "customer_support": "support unhelpful, unreachable, only a bot, or rude",
    "app_payment_bugs": "app crashes or lags, login or OTP trouble, failed payment, money deducted, location bugs",
    "out_of_stock": "items unavailable or out of stock",
    "other": "a complaint that fits none of the above",
    "no_complaint": "no complaint at all, for example praise left with a low star rating",
}
