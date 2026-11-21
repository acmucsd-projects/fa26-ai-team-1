"""Collect earnings-release events (8-K Item 2.02) from SEC EDGAR.

Source: https://data.sec.gov/submissions/CIK##########.json
Checked 2026-11-20 against the EDGAR filing header for AAPL 0000320193-24-000080:
  submissions JSON acceptanceDateTime = 2024-08-01T20:30:26.000Z  (real UTC)
  filing header ACCEPTANCE-DATETIME   = 20240801163026             (US/Eastern)
So the JSON value must be converted from UTC to America/New_York.
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.sec.gov/submissions/"
ET = "America/New_York"


def fetch_json(url, user_agent, cache_path):
    """Download a JSON file once and keep the raw copy on disk."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=30)
    resp.raise_for_status()
    time.sleep(0.2)  # SEC fair-access limit is 10 requests per second
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(resp.text)
    return resp.json()


def get_filings(cik, user_agent, cache_dir):
    """All filings for one CIK as a DataFrame (recent block + older pages)."""
    name = f"CIK{int(cik):010d}.json"
    sub = fetch_json(BASE + name, user_agent, Path(cache_dir) / name)
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        blocks.append(fetch_json(BASE + f["name"], user_agent, Path(cache_dir) / f["name"]))
    df = pd.concat([pd.DataFrame(b) for b in blocks], ignore_index=True)
    df["cik"] = int(cik)
    df["company"] = sub.get("name", "")
    return df


def earnings_events(filings):
    """Keep original 8-Ks that report Item 2.02 (Results of Operations)."""
    df = filings[(filings["form"] == "8-K") & filings["items"].str.contains("2.02", regex=False)].copy()
    utc = pd.to_datetime(df["acceptanceDateTime"], utc=True)
    df["accepted_et"] = utc.dt.tz_convert(ET)
    df["session"] = df["accepted_et"].apply(classify_session)
    df = df.rename(columns={"accessionNumber": "accession", "filingDate": "filing_date",
                            "primaryDocument": "primary_doc"})
    cols = ["cik", "company", "accession", "filing_date", "accepted_et", "session", "items", "primary_doc"]
    return df[cols].sort_values("accepted_et").reset_index(drop=True)


def classify_session(ts):
    """pre_market (< 9:30 ET), after_close (>= 16:00 ET), else intraday.
    Weekend/holiday timestamps are still labelled by clock time; first_trade_date handles the date."""
    minutes = ts.hour * 60 + ts.minute
    if minutes < 9 * 60 + 30:
        return "pre_market"
    if minutes >= 16 * 60:
        return "after_close"
    return "intraday"


def first_trade_date(ts, trading_days):
    """First trading day whose OPEN comes after the release.
    trading_days: sorted list/Index of dates taken from the price data (so holidays are handled).
    pre_market -> same day if it trades; after_close or intraday -> next trading day."""
    days = pd.DatetimeIndex(trading_days).normalize()
    d = pd.Timestamp(ts.date())
    if classify_session(ts) != "pre_market":
        d = d + pd.Timedelta(days=1)
    pos = days.searchsorted(d)
    return days[pos] if pos < len(days) else pd.NaT
