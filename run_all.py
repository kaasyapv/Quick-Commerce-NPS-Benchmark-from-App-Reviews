"""Run every step after the review pull and the tagging, in order. Stops at the first failure."""
import subprocess, sys
from pathlib import Path

STEPS = ["src/sample.py", "src/nps.py", "src/driver_mix.py", "src/bridge.py", "src/robust.py",
         "src/baseline.py", "src/quotes.py", "src/logos.py", "src/deck_charts.py", "src/deck.py"]

for step in STEPS:
    print(f"\n=== {step} ===")
    subprocess.run([sys.executable, step], check=True, cwd=Path(__file__).parent)
