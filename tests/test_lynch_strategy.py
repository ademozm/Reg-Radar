import pytest

from config import settings
from lynch_strategy import LynchScore, _classify_category, evaluate_lynch_criteria


def _lynch_ideal_stock() -> dict:
    return {
        "trailing_pe": 15.0, "earnings_growth": 0.20, "revenue_growth": 0.22,
        "debt_to_equity": 30.0, "dividend_yield": 0.01, "held_percent_institutions": 0.40,
        "profit_margins": 0.12, "sector": "Technology",
    }


def test_ideal_stock_passes_all_criteria():
    score = evaluate_lynch_criteria("IDEAL", _lynch_ideal_stock())
    assert score.peg is not None and score.peg <= 1.0
    assert all(score.criteria.values())
    assert score.recommendation is True


def test_overvalued_stock_fails_peg():
    data = _lynch_ideal_stock()
    data["trailing_pe"] = 60.0
    score = evaluate_lynch_criteria("PAHALI", data)
    assert score.peg == 3.0
    assert score.criteria["peg_uygun"] is False


def test_too_much_debt_fails():
    data = _lynch_ideal_stock()
    data["debt_to_equity"] = 150.0
    score = evaluate_lynch_criteria("BORCLU", data)
    assert score.criteria["borc_makul"] is False


def test_unsustainable_growth_fails():
    data = _lynch_ideal_stock()
    data["earnings_growth"] = 0.80
    score = evaluate_lynch_criteria("ASIRI", data)
    assert score.criteria["buyume_surdurulebilir"] is False


def test_too_slow_growth_fails():
    data = _lynch_ideal_stock()
    data["earnings_growth"] = 0.05
    score = evaluate_lynch_criteria("YAVAS", data)
    assert score.criteria["buyume_surdurulebilir"] is False


def test_missing_data_not_recommended():
    score = evaluate_lynch_criteria("VERISIZ", {})
    assert score.peg is None
    assert score.recommendation is False


def test_error_never_recommends():
    score = LynchScore(symbol="HATALI")
    score.error = "veri çekilemedi"
    score.criteria = {"a": True, "b": True, "c": True, "d": True, "e": True}
    assert score.recommendation is False


def test_market_detection_turkey():
    score = evaluate_lynch_criteria("THYAO.IS", _lynch_ideal_stock())
    assert score.market == "TR"


def test_market_detection_us():
    score = evaluate_lynch_criteria("AAPL", _lynch_ideal_stock())
    assert score.market == "US"


def test_position_in_52w_range():
    score = evaluate_lynch_criteria("IDEAL", _lynch_ideal_stock())
    score.current_price, score.fifty_two_week_low, score.fifty_two_week_high = 75.0, 50.0, 100.0
    assert score.position_in_52w_range_pct == 50.0


def test_upside_to_target():
    score = evaluate_lynch_criteria("IDEAL", _lynch_ideal_stock())
    score.current_price, score.target_mean_price = 100.0, 120.0
    assert score.upside_to_target_pct == 20.0


def test_classify_category_cyclical():
    assert _classify_category({"sector": "Energy", "revenue_growth": 0.30, "trailing_pe": 10}) == "cyclical"


def test_classify_category_fast_grower():
    assert _classify_category({"sector": "Technology", "revenue_growth": 0.25, "trailing_pe": 20}) == "fast_grower"


def test_min_criteria_threshold(monkeypatch):
    monkeypatch.setattr(settings, "LYNCH_MIN_CRITERIA_PASSED", 5)
    data = _lynch_ideal_stock()
    data["profit_margins"] = -0.01
    score = evaluate_lynch_criteria("DORTBES", data)
    assert score.criteria_passed_count == 4
    assert score.recommendation is False


def test_dividend_yield_as_fraction_normalized_correctly():
    """yfinance oran olarak (0.03 = %3) döndürürse doğrudan *100 ile çevrilmeli."""
    data = _lynch_ideal_stock()
    data["dividend_yield"] = 0.03
    score = evaluate_lynch_criteria("ORAN", data)
    assert score.dividend_yield_pct == pytest.approx(3.0, abs=0.01)


def test_dividend_yield_already_percent_normalized_correctly():
    """
    yfinance bazı sürümlerde temettü verimini zaten yüzde olarak (3.42 = %3.42)
    döndürüyor - bunu tekrar 100 ile çarpıp %342 gibi anlamsız bir sonuç
    üretmemeliyiz (gerçek hayatta yaşanan bug, TUPRS.IS örneği).
    """
    data = _lynch_ideal_stock()
    data["dividend_yield"] = 3.42
    score = evaluate_lynch_criteria("YUZDE", data)
    assert score.dividend_yield_pct == pytest.approx(3.42, abs=0.01)
    assert score.dividend_yield_pct < 100  # asıl regresyon koruması


def test_institutional_ownership_as_fraction_normalized_correctly():
    data = _lynch_ideal_stock()
    data["held_percent_institutions"] = 0.40
    score = evaluate_lynch_criteria("ORAN2", data)
    assert score.institutional_ownership_pct == pytest.approx(40.0, abs=0.01)


def test_institutional_ownership_already_percent_normalized_correctly():
    data = _lynch_ideal_stock()
    data["held_percent_institutions"] = 40.0
    score = evaluate_lynch_criteria("YUZDE2", data)
    assert score.institutional_ownership_pct == pytest.approx(40.0, abs=0.01)


def test_scan_symbol_retries_then_succeeds(monkeypatch):
    from lynch_strategy import scan_symbol

    calls = {"n": 0}

    def flaky_fetch(symbol):
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("Expecting value: line 1 column 1 (char 0)")
        return _lynch_ideal_stock()

    monkeypatch.setattr("lynch_strategy.clear_yfinance_cache", lambda: "/tmp/fake")
    monkeypatch.setattr(settings, "LYNCH_RETRY_BACKOFF_BASE_SECONDS", 0.01)
    score = scan_symbol("AAPL", fetch_fn=flaky_fetch)

    assert score.error is None
    assert calls["n"] == 2


def test_scan_symbol_gives_up_after_max_retries(monkeypatch):
    from lynch_strategy import scan_symbol

    def always_fails(symbol):
        raise RuntimeError("429 Too Many Requests")

    monkeypatch.setattr("lynch_strategy.clear_yfinance_cache", lambda: "/tmp/fake")
    monkeypatch.setattr(settings, "LYNCH_RETRY_BACKOFF_BASE_SECONDS", 0.01)
    monkeypatch.setattr(settings, "LYNCH_MAX_RETRIES", 2)
    score = scan_symbol("AAPL", fetch_fn=always_fails)

    assert score.error is not None
    assert score.recommendation is False
