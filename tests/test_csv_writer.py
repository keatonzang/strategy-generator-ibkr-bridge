from dataclasses import dataclass
from datetime import datetime, date

from src.csv_writer import bars_to_csv, CSV_HEADER


@dataclass
class FakeBar:
    date: object
    open: float
    high: float
    low: float
    close: float
    volume: float


def test_header_is_fixed():
    assert CSV_HEADER == "datetime,Open,High,Low,Close,volume,openinterest"


def test_empty_bars_produces_just_header():
    assert bars_to_csv([]).strip() == CSV_HEADER


def test_intraday_datetime_formatted_with_time():
    bars = [
        FakeBar(datetime(2024, 1, 2, 9, 30), 100.0, 101.0, 99.5, 100.5, 12345),
    ]
    csv = bars_to_csv(bars)
    assert "2024-01-02 09:30:00,100.0,101.0,99.5,100.5,12345,0" in csv


def test_daily_date_gets_midnight_time():
    bars = [
        FakeBar(date(2024, 1, 2), 100.0, 101.0, 99.5, 100.5, 12345),
    ]
    csv = bars_to_csv(bars)
    assert "2024-01-02 00:00:00,100.0,101.0,99.5,100.5,12345,0" in csv


def test_openinterest_is_always_zero():
    bars = [FakeBar(date(2024, 1, 2), 1.0, 1.0, 1.0, 1.0, 1)]
    assert bars_to_csv(bars).strip().endswith(",0")


def test_volume_is_integer_in_output():
    bars = [FakeBar(date(2024, 1, 2), 1.0, 1.0, 1.0, 1.0, 1234.0)]
    assert ",1234,0" in bars_to_csv(bars)
