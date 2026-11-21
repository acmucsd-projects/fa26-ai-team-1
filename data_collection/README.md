# Data collection step 1: earnings-release timestamps from EDGAR

Goal: one row per earnings release (8-K with Item 2.02), with the exact acceptance time in US/Eastern
and the session (pre_market / intraday / after_close). This feeds the event timing rules and the
three-segment labels (overnight, day1, drift).

## Files
- `src/edgar.py` - download submissions JSON (cached raw in `data/raw/edgar/`), filter 8-K Item 2.02,
  convert time to US/Eastern, classify session, map to first tradeable open using price-data trading days.
- `scripts/collect_events.py` - `universe.csv` -> `data/events_8k_202.csv`.
- `universe_pilot.csv` - 8 pilot firms keyed by CIK (3 delisted on purpose).
- `tests/test_edgar.py` - 3 tests, using real AAPL rows.
- `data/events_8k_202_pilot.csv` - pilot output, 2015-2024, 309 events.

## Run
    pip install -r requirements.txt
    set SEC_USER_AGENT=Your Name your_email@ucsd.edu      (PowerShell: $env:SEC_USER_AGENT="...")
    python scripts/collect_events.py --universe universe_pilot.csv
    python -m pytest -q

## Verified facts (checked 2026-11-20)
- `acceptanceDateTime` in the submissions JSON is real UTC, not Eastern. AAPL 0000320193-24-000080:
  JSON `2024-08-01T20:30:26Z`, filing header `ACCEPTANCE-DATETIME 20240801163026` (Eastern).
  Apple's winter releases show 21:30Z, so DST is applied, which confirms UTC.
- `items` is filled for 8-Ks back to at least 2011 (AAPL, XLNX checked).
- Delisted firms (XLNX, CTXS, VMW) have an empty ticker list at SEC, so the universe must be keyed by CIK,
  not looked up from `company_tickers.json`.
- Older filings live in extra pages (`filings.files`); the code reads them too.

## Pilot results (8 firms, 2015-2024)
- 309 events: 295 after_close, 14 pre_market, 0 intraday.
- CTXS moved to pre-market releases in 2019-2021; AMD, NVDA, VMW have a few pre-market ones.
- 16 events come less than 45 days after the previous one for the same firm. These are probably
  pre-announcements or 8-Ks that attach Item 2.02 to other news (not opened yet). Open question below.

## Open choices (not decided here)
1. What to do with extra Item 2.02 8-Ks (pre-announcements): keep as separate events, drop them,
   or keep only the one closest to the 10-Q/10-K for that quarter.
2. Point-in-time S&P 500 IT membership list: source not chosen yet. `universe_pilot.csv` is only a pilot.
3. 8-K/A amendments are dropped (only original `8-K` is kept).
