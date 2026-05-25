"""
Downloads public real estate data from Zillow Research and saves to data/raw/.
Run this first before clean_data.py.
"""

import os
import urllib.request

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

SOURCES = {
    # Zillow Observed Rent Index — metro level, monthly
    "zillow_zori_metro.csv": (
        "https://files.zillowstatic.com/research/public_csvs/zori/"
        "Metro_zori_uc_sfrcondomfr_sm_sa_month.csv"
    ),
    # Zillow Home Value Index — metro level, monthly
    "zillow_zhvi_metro.csv": (
        "https://files.zillowstatic.com/research/public_csvs/zhvi/"
        "Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    ),
}


def download(name, url):
    dest = os.path.join(RAW_DIR, name)
    if os.path.exists(dest):
        print(f"  [skip] {name} already downloaded")
        return
    print(f"  Downloading {name} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        print(f"  [ok] {name}")
    except Exception as e:
        print(f"  [error] {name}: {e}")
        print(f"         Download manually from: {url}")


if __name__ == "__main__":
    print("Fetching Zillow Research data...")
    for name, url in SOURCES.items():
        download(name, url)
    print("\nDone. Run scripts/clean_data.py next.")
