"""
scheduler.py'nin orkestrasyon mantığı için testler. Gerçek DB ve yfinance
çağrılarının yerine sahte (mock) fonksiyonlar konuyor - amaç "otomatik
tarama kapalıyken hiç taramamalı" gibi davranışsal garantileri kanıtlamak.
"""
from lynch_strategy import LynchScore
from scheduler import _run_scan_for_market


def test_auto_scan_disabled_skips_entirely(monkeypatch):
    monkeypatch.setattr(
        "scheduler.get_app_settings",
        lambda: {"auto_scan_enabled": False, "watchlist_us": "AAPL", "watchlist_tr": ""},
    )

    scan_calls = []
    monkeypatch.setattr("scheduler.scan_symbol", lambda symbol, fetch_fn=None: scan_calls.append(symbol))
    monkeypatch.setattr("scheduler.persist_scan_result", lambda score: None)
    monkeypatch.setattr("scheduler.notify", lambda message: None)

    _run_scan_for_market("ABD", ["AAPL", "MSFT"], notify_key="US")

    assert scan_calls == []  # kapalıyken hiçbir sembol taranmamalı


def test_auto_scan_enabled_scans_all_symbols(monkeypatch):
    monkeypatch.setattr(
        "scheduler.get_app_settings",
        lambda: {"auto_scan_enabled": True, "watchlist_us": "AAPL,MSFT", "watchlist_tr": ""},
    )

    scan_calls = []

    def fake_scan(symbol, fetch_fn=None):
        scan_calls.append(symbol)
        return LynchScore(symbol=symbol)

    monkeypatch.setattr("scheduler.scan_symbol", fake_scan)
    monkeypatch.setattr("scheduler.persist_scan_result", lambda score: None)
    monkeypatch.setattr("scheduler.mark_notification_sent", lambda market: None)

    sent_messages = []
    monkeypatch.setattr("scheduler.notify", lambda message: sent_messages.append(message))
    monkeypatch.setattr("scheduler.time.sleep", lambda seconds: None)  # testte gerçekten beklemeyelim

    _run_scan_for_market("ABD", ["AAPL", "MSFT"], notify_key="US")

    assert scan_calls == ["AAPL", "MSFT"]
    assert len(sent_messages) == 1
    assert "ABD" in sent_messages[0]


def test_empty_watchlist_skips_without_error(monkeypatch):
    monkeypatch.setattr(
        "scheduler.get_app_settings",
        lambda: {"auto_scan_enabled": True, "watchlist_us": "", "watchlist_tr": ""},
    )
    scan_calls = []
    monkeypatch.setattr("scheduler.scan_symbol", lambda symbol, fetch_fn=None: scan_calls.append(symbol))

    _run_scan_for_market("ABD", [], notify_key="US")

    assert scan_calls == []
