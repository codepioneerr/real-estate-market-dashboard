"""
Step 5: Master pipeline runner — runs all steps end-to-end.

Usage:
    python scripts/run_pipeline.py           # full pipeline
    python scripts/run_pipeline.py --skip-fetch   # skip Zillow download
    python scripts/run_pipeline.py --only excel   # only rebuild Excel dashboard

Cron example (daily at 6 AM):
    0 6 * * * /usr/bin/python3 /path/to/scripts/run_pipeline.py >> /tmp/re_pipeline.log 2>&1
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent.parent
PYTHON = sys.executable


def run(label, args, **kwargs):
    start = time.time()
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    result = subprocess.run(args, **kwargs)
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"\n[ERROR] {label} failed (exit {result.returncode})")
        sys.exit(result.returncode)
    print(f"  ✓ Done in {elapsed:.1f}s")
    return result


def main():
    parser = argparse.ArgumentParser(description="Real Estate Pipeline Runner")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Skip Zillow data download (use cached raw files)")
    parser.add_argument("--only", choices=["fetch", "clean", "sql", "forecast", "excel", "app"],
                        help="Run only one step")
    args = parser.parse_args()

    scripts = BASE / "scripts"
    cwd = str(BASE)

    steps = {
        "fetch":    ([PYTHON, str(scripts / "fetch_data.py")],    "Fetch Zillow data"),
        "clean":    ([PYTHON, str(scripts / "clean_data.py")],    "Clean & transform data"),
        "sql":      ([PYTHON, str(scripts / "load_to_sql.py")],   "Load to SQLite"),
        "forecast": ([PYTHON, str(scripts / "forecast.py")],      "Generate rent forecast"),
        "excel":    ([PYTHON, str(scripts / "build_dashboard.py")],"Build Excel dashboard"),
    }

    if args.only:
        cmd, label = steps[args.only]
        run(label, cmd, cwd=cwd)
        print(f"\nPipeline complete (--only {args.only}).")
        return

    total_start = time.time()

    if not args.skip_fetch:
        cmd, label = steps["fetch"]
        run(label, cmd, cwd=cwd)
    else:
        print("\n[skip] fetch_data.py (--skip-fetch)")

    for key in ("clean", "sql", "forecast", "excel"):
        cmd, label = steps[key]
        run(label, cmd, cwd=cwd)

    elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {elapsed:.1f}s")
    print(f"  Excel: {BASE}/dashboard/Real_Estate_Market_Dashboard.xlsx")
    print(f"  DB:    {BASE}/data/real_estate.db")
    print(f"  App:   streamlit run {BASE}/app.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
