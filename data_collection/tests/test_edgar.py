import pandas as pd

from src.edgar import classify_session, earnings_events, first_trade_date

# Rows copied from the real AAPL submissions JSON (CIK 320193), plus two rows that must be dropped.
FILINGS = pd.DataFrame({
    "cik": 320193, "company": "Apple Inc.",
    "accessionNumber": ["0000320193-24-000080", "0000320193-24-000005", "x-amend", "x-other"],
    "filingDate": ["2024-08-01", "2024-02-01", "2024-02-02", "2024-03-01"],
    "acceptanceDateTime": ["2024-08-01T20:30:26.000Z", "2024-02-01T21:30:30.000Z",
                           "2024-02-02T21:00:00.000Z", "2024-03-01T21:00:00.000Z"],
    "form": ["8-K", "8-K", "8-K/A", "8-K"],
    "items": ["2.02,9.01", "2.02,9.01", "2.02", "5.07"],
    "primaryDocument": ["aapl-20240801.htm", "aapl-20240201.htm", "a.htm", "b.htm"],
})


def test_filter_and_utc_to_eastern():
    ev = earnings_events(FILINGS)
    assert list(ev["accession"]) == ["0000320193-24-000005", "0000320193-24-000080"]
    # Summer (EDT, UTC-4) and winter (EST, UTC-5) both land on Apple's 4:30 pm ET release.
    assert [t.strftime("%H:%M") for t in ev["accepted_et"]] == ["16:30", "16:30"]
    assert set(ev["session"]) == {"after_close"}


def test_classify_session():
    t = lambda s: pd.Timestamp(s, tz="America/New_York")
    assert classify_session(t("2024-05-01 07:00")) == "pre_market"
    assert classify_session(t("2024-05-01 09:30")) == "intraday"
    assert classify_session(t("2024-05-01 15:59")) == "intraday"
    assert classify_session(t("2024-05-01 16:00")) == "after_close"


def test_first_trade_date_skips_weekend_and_holiday():
    # 2024-07-04 is a market holiday; 07-06/07 is a weekend.
    days = pd.to_datetime(["2024-07-02", "2024-07-03", "2024-07-05", "2024-07-08"])
    t = lambda s: pd.Timestamp(s, tz="America/New_York")
    assert first_trade_date(t("2024-07-03 16:05"), days) == pd.Timestamp("2024-07-05")
    assert first_trade_date(t("2024-07-05 08:00"), days) == pd.Timestamp("2024-07-05")
    assert first_trade_date(t("2024-07-05 17:00"), days) == pd.Timestamp("2024-07-08")
    assert first_trade_date(t("2024-07-06 10:00"), days) == pd.Timestamp("2024-07-08")
