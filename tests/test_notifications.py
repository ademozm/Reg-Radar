from lynch_strategy import LynchScore
from notifications import build_scan_summary_message


def _score(symbol, peg=0.8, criteria_passed=5, error=None):
    s = LynchScore(symbol=symbol)
    s.peg = peg
    s.criteria = {f"k{i}": (i < criteria_passed) for i in range(5)}
    s.error = error
    return s


def test_summary_with_candidates():
    scores = [_score("AAPL", peg=0.8), _score("MSFT", peg=1.5, criteria_passed=2)]
    msg = build_scan_summary_message("ABD", scores)
    assert "2 hisse tarandı" in msg
    assert "1 aday bulundu" in msg
    assert "AAPL" in msg
    assert "MSFT" not in msg  # MSFT aday değil (2/5 kriter), listelenmemeli


def test_summary_no_candidates():
    scores = [_score("XYZ", peg=2.0, criteria_passed=1)]
    msg = build_scan_summary_message("Türkiye", scores)
    assert "0 aday bulundu" in msg
    assert "Adaylar:" not in msg


def test_summary_reports_errors():
    scores = [_score("AAPL", peg=0.8), _score("BAD", error="429 Too Many Requests")]
    msg = build_scan_summary_message("ABD", scores)
    assert "1 sembol için veri alınamadı" in msg
    assert "BAD" in msg


def test_summary_candidates_sorted_by_peg():
    scores = [_score("HIGH", peg=0.95), _score("LOW", peg=0.3)]
    msg = build_scan_summary_message("ABD", scores)
    assert msg.index("LOW") < msg.index("HIGH")
