# Quick-Commerce NPS Benchmark from App Reviews

Monthly NPS proxy for Blinkit, Zepto and Swiggy Instamart, built from every public Google Play review posted between Jan 2025 and Sep 2026. Each detractor complaint driver is priced in NPS points.

_Work in progress. Findings land here once the analysis runs._

## Run
```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/pull_reviews.py   # long: run overnight
python run_all.py            # everything after the pull
```
