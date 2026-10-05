"""Run every step after the review pull, in order. Stops at the first failure."""
import subprocess, sys
from pathlib import Path

STEPS = []  # filled in phase by phase, e.g. "src/nps.py"

for step in STEPS:
    print(f"\n=== {step} ===")
    subprocess.run([sys.executable, step], check=True, cwd=Path(__file__).parent)
