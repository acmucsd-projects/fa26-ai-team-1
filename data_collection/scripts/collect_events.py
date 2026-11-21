"""universe.csv -> data/events_8k_202.csv

Usage: python scripts/collect_events.py --universe universe_pilot.csv --start 2015-01-01 --end 2024-12-31
Set SEC_USER_AGENT to "Name email" first (SEC rejects requests without a real contact).
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.edgar import earnings_events, get_filings  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--universe", default="universe_pilot.csv")
p.add_argument("--start", default="2015-01-01")
p.add_argument("--end", default="2024-12-31")
p.add_argument("--out", default="data/events_8k_202.csv")
args = p.parse_args()

ua = os.environ.get("SEC_USER_AGENT")
if not ua:
    sys.exit("Set SEC_USER_AGENT, e.g. 'Jane Doe jane@ucsd.edu'")

universe = pd.read_csv(args.universe)
frames = []
for row in universe.itertuples():
    ev = earnings_events(get_filings(row.cik, ua, "data/raw/edgar"))
    ev.insert(0, "ticker", row.ticker)
    frames.append(ev)
    print(f"{row.ticker}: {len(ev)} events")

events = pd.concat(frames, ignore_index=True)
day = events["accepted_et"].dt.strftime("%Y-%m-%d")
events = events[(day >= args.start) & (day <= args.end)]
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
events.to_csv(args.out, index=False)
print(f"saved {len(events)} events to {args.out}")
print(events["session"].value_counts().to_string())
