"""
Peter Lynch tarzı temel analiz (fundamental) tarama motoru.

Bu modül bilerek Streamlit'ten habersiz (framework-agnostic) yazıldı -
hem `pytest` ile ağsız test edilebilsin hem de ileride başka bir arayüze
(CLI, farklı bir web framework) taşınabilsin diye. Önbellekleme (caching)
app.py tarafında, bu modülün DIŞINDA yapılıyor.

ÖNEMLİ DÜRÜSTLÜK NOTU:
Lynch'in gerçek yönteminin büyük kısmı NİTELİKSEL'di: mağazaları gezmek,
ürünü/işi anlamak, yönetimle konuşmak, "hikayeyi" değerlendirmek. Bu kod
SADECE onun checklist'inin NİCEL (sayısal) kısmını otomatikleştiriyor.
"Aday" işaretli bir hisse yatırım tavsiyesi değil, araştırmanın başlangıç
noktasıdır.
"""
import json
import logging
import random
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs

from config import settings
from database import LynchScanResult, SessionLocal

logger = logging.getLogger(__name__)


def clear_yfinance_cache() -> Path:
    """
    yfinance'in kalıcı çerez/crumb önbelleğini siler. Yahoo Finance bir kere
    "Too Many Requests" döndürdüğünde yfinance bunu bazen geçerli bir crumb
    (kimlik doğrulama jetonu) sanıp diske kaydediyor ve sonraki her istekte
    bozuk jetonu tekrar kullanıyor (bilinen kütüphane hatası). Bu fonksiyon
    o önbelleği temizleyerek bir sonraki isteğin sıfırdan kimlik doğrulaması
    yapmasını zorluyor.
    """
    cache_dir = Path(platformdirs.user_cache_dir()) / "py-yfinance"
    shutil.rmtree(cache_dir, ignore_errors=True)
    return cache_dir


@dataclass
class LynchScore:
    symbol: str
    market: str = "US"                 # "US" | "TR"
    company_name: str | None = None
    currency: str | None = None
    sector: str | None = None
    category: str = "unknown"

    peg: float | None = None
    pegy: float | None = None
    pe_ratio: float | None = None
    eps_growth_pct: float | None = None
    debt_to_equity: float | None = None
    institutional_ownership_pct: float | None = None
    criteria: dict[str, bool] = field(default_factory=dict)

    current_price: float | None = None
    day_change_pct: float | None = None
    fifty_two_week_low: float | None = None
    fifty_two_week_high: float | None = None
    average_volume: float | None = None
    market_cap: float | None = None
    price_to_book: float | None = None
    return_on_equity_pct: float | None = None
    current_ratio: float | None = None
    dividend_yield_pct: float | None = None
    target_mean_price: float | None = None
    recommendation_key: str | None = None

    error: str | None = None

    @property
    def position_in_52w_range_pct(self) -> float | None:
        if self.fifty_two_week_low is None or self.fifty_two_week_high is None or self.current_price is None:
            return None
        span = self.fifty_two_week_high - self.fifty_two_week_low
        if span <= 0:
            return None
        return round((self.current_price - self.fifty_two_week_low) / span * 100, 1)

    @property
    def upside_to_target_pct(self) -> float | None:
        if self.target_mean_price is None or not self.current_price:
            return None
        return round((self.target_mean_price / self.current_price - 1) * 100, 1)

    @property
    def criteria_passed_count(self) -> int:
        return sum(1 for v in self.criteria.values() if v)

    @property
    def criteria_total(self) -> int:
        return len(self.criteria)

    @property
    def recommendation(self) -> bool:
        if self.error:
            return False
        return self.criteria_passed_count >= settings.LYNCH_MIN_CRITERIA_PASSED


def _market_for_symbol(symbol: str) -> str:
    return "TR" if symbol.upper().endswith(".IS") else "US"


def fetch_fundamentals(symbol: str) -> dict:
    """
    yfinance üzerinden temel + trade verilerini çeker.

    Bu fonksiyon bilerek KÜÇÜK ve SAF tutuldu (sadece veri çekip dict
    döndürüyor) ki app.py bunu doğrudan st.cache_data ile sarabilsin.
    """
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    info = ticker.info

    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    previous_close = info.get("previousClose")
    day_change_pct = None
    if current_price and previous_close:
        day_change_pct = round((current_price / previous_close - 1) * 100, 2)

    return {
        "long_name": info.get("longName") or info.get("shortName"),
        "currency": info.get("currency"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "earnings_growth": info.get("earningsGrowth"),
        "revenue_growth": info.get("revenueGrowth"),
        "debt_to_equity": info.get("debtToEquity"),
        "dividend_yield": info.get("dividendYield"),
        "held_percent_institutions": info.get("heldPercentInstitutions"),
        "profit_margins": info.get("profitMargins"),
        "market_cap": info.get("marketCap"),
        "current_price": current_price,
        "day_change_pct": day_change_pct,
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "average_volume": info.get("averageVolume"),
        "price_to_book": info.get("priceToBook"),
        "return_on_equity": info.get("returnOnEquity"),
        "current_ratio": info.get("currentRatio"),
        "target_mean_price": info.get("targetMeanPrice"),
        "recommendation_key": info.get("recommendationKey"),
    }


def _classify_category(data: dict) -> str:
    """Lynch'in altı kategorisine kaba bir sezgisel eşleme - kesin değil, bağlam içindir."""
    growth = data.get("revenue_growth") or 0
    sector = (data.get("sector") or "").lower()
    pe = data.get("trailing_pe")

    cyclical_sectors = {"basic materials", "energy", "industrials", "consumer cyclical"}
    if sector in cyclical_sectors:
        return "cyclical"
    if growth is not None and growth >= 0.20:
        return "fast_grower"
    if growth is not None and 0.10 <= growth < 0.20:
        return "stalwart"
    if pe is not None and pe > 0 and growth is not None and growth < 0.10:
        return "slow_grower"
    return "unknown"


def evaluate_lynch_criteria(symbol: str, data: dict) -> LynchScore:
    """Saf fonksiyon: ağ çağrısı yapmaz, sadece zaten çekilmiş veriyi değerlendirir (ağsız test edilebilir)."""
    score = LynchScore(symbol=symbol, market=_market_for_symbol(symbol))

    pe = data.get("trailing_pe")
    earnings_growth = data.get("earnings_growth")
    eps_growth_pct = earnings_growth * 100 if earnings_growth is not None else None
    debt_to_equity_raw = data.get("debt_to_equity")
    debt_to_equity = debt_to_equity_raw / 100 if debt_to_equity_raw is not None else None
    dividend_yield_raw = data.get("dividend_yield")
    # yfinance sürümüne/uca göre temettü verimi bazen oran (0.03 = %3),
    # bazen zaten yüzde (3.0 = %3) olarak geliyor - bu tutarsızlık
    # yfinance'in farklı sürümleri arasında değişebiliyor. Gerçek bir
    # hissenin temettü verimi oran olarak neredeyse hiçbir zaman 1'i
    # (yani %100'ü) geçmez, bu yüzden 1'den büyükse zaten yüzde kabul
    # edip orana çeviriyoruz - aksi halde %342 gibi anlamsız değerler
    # çıkıyordu (bkz. TUPRS.IS örneği).
    if dividend_yield_raw is None:
        dividend_yield = 0.0
    elif dividend_yield_raw > 1:
        dividend_yield = dividend_yield_raw / 100
    else:
        dividend_yield = dividend_yield_raw
    held_pct_raw = data.get("held_percent_institutions")
    # Aynı format tutarsızlığı kurumsal sahiplik için de geçerli - bir
    # oran (%100'ü geçemez) olduğu için aynı korumayı uyguluyoruz.
    if held_pct_raw is None:
        institutional_pct = None
    elif held_pct_raw > 1:
        institutional_pct = held_pct_raw
    else:
        institutional_pct = held_pct_raw * 100
    roe_pct = data.get("return_on_equity") * 100 if data.get("return_on_equity") is not None else None

    score.company_name = data.get("long_name")
    score.currency = data.get("currency")
    score.sector = data.get("sector")
    score.category = _classify_category(data)

    score.pe_ratio = pe
    score.eps_growth_pct = eps_growth_pct
    score.debt_to_equity = debt_to_equity
    score.institutional_ownership_pct = institutional_pct

    score.current_price = data.get("current_price")
    score.day_change_pct = data.get("day_change_pct")
    score.fifty_two_week_low = data.get("fifty_two_week_low")
    score.fifty_two_week_high = data.get("fifty_two_week_high")
    score.average_volume = data.get("average_volume")
    score.market_cap = data.get("market_cap")
    score.price_to_book = data.get("price_to_book")
    score.return_on_equity_pct = roe_pct
    score.current_ratio = data.get("current_ratio")
    score.dividend_yield_pct = (dividend_yield * 100) if dividend_yield is not None else None
    score.target_mean_price = data.get("target_mean_price")
    score.recommendation_key = data.get("recommendation_key")

    if pe is not None and eps_growth_pct and eps_growth_pct > 0:
        score.peg = round(pe / eps_growth_pct, 3)
        score.pegy = round(pe / (eps_growth_pct + dividend_yield * 100), 3)

    score.criteria["peg_uygun"] = score.peg is not None and score.peg <= settings.LYNCH_MAX_PEG
    score.criteria["buyume_surdurulebilir"] = (
        eps_growth_pct is not None
        and settings.LYNCH_MIN_EPS_GROWTH_PCT <= eps_growth_pct <= settings.LYNCH_MAX_EPS_GROWTH_PCT
    )
    score.criteria["borc_makul"] = (
        debt_to_equity is not None and debt_to_equity <= settings.LYNCH_MAX_DEBT_TO_EQUITY
    )
    score.criteria["karli"] = (data.get("profit_margins") or 0) > 0
    score.criteria["buyume_alani_var"] = (
        institutional_pct is None or institutional_pct <= settings.LYNCH_MAX_INSTITUTIONAL_OWNERSHIP_PCT
    )

    return score


def scan_symbol(symbol: str, fetch_fn=fetch_fundamentals) -> LynchScore:
    """
    Bir sembolü uçtan uca tarar. `fetch_fn` parametresi test edilebilirlik
    VE app.py'nin kendi cache'lenmiş fetch fonksiyonunu enjekte edebilmesi
    için var - varsayılan olarak ham (cache'siz) fetch_fundamentals kullanılır.
    """
    last_error = None
    cache_cleared = False

    for attempt in range(settings.LYNCH_MAX_RETRIES):
        try:
            data = fetch_fn(symbol)
            return evaluate_lynch_criteria(symbol, data)
        except Exception as exc:
            last_error = exc
            is_last_attempt = attempt == settings.LYNCH_MAX_RETRIES - 1

            if not cache_cleared:
                cleared_path = clear_yfinance_cache()
                cache_cleared = True
                logger.warning("%s: 1. deneme başarısız, yfinance önbelleği temizlendi (%s)", symbol, cleared_path)

            if is_last_attempt:
                break

            backoff = settings.LYNCH_RETRY_BACKOFF_BASE_SECONDS * (2 ** attempt) + random.uniform(0, 2)
            logger.warning("%s: %d. deneme başarısız (%s), %.1f sn sonra tekrar denenecek",
                            symbol, attempt + 1, exc, backoff)
            time.sleep(backoff)

    logger.warning("%s: tüm denemeler tükendi - %s", symbol, last_error)
    score = LynchScore(symbol=symbol, market=_market_for_symbol(symbol))
    score.error = str(last_error)
    return score


def persist_scan_result(score: LynchScore) -> None:
    db = SessionLocal()
    try:
        db.add(LynchScanResult(
            symbol=score.symbol, market=score.market, company_name=score.company_name,
            currency=score.currency, sector=score.sector, category=score.category,
            peg=score.peg, pegy=score.pegy, pe_ratio=score.pe_ratio,
            eps_growth_pct=score.eps_growth_pct, debt_to_equity=score.debt_to_equity,
            institutional_ownership_pct=score.institutional_ownership_pct,
            criteria_passed_count=score.criteria_passed_count, criteria_total=score.criteria_total,
            criteria_detail=json.dumps(score.criteria), recommendation=score.recommendation,
            current_price=score.current_price, day_change_pct=score.day_change_pct,
            fifty_two_week_low=score.fifty_two_week_low, fifty_two_week_high=score.fifty_two_week_high,
            position_in_52w_range_pct=score.position_in_52w_range_pct, average_volume=score.average_volume,
            market_cap=score.market_cap, price_to_book=score.price_to_book,
            return_on_equity_pct=score.return_on_equity_pct, current_ratio=score.current_ratio,
            dividend_yield_pct=score.dividend_yield_pct, target_mean_price=score.target_mean_price,
            upside_to_target_pct=score.upside_to_target_pct, recommendation_key=score.recommendation_key,
            error=score.error,
        ))
        db.commit()
    finally:
        db.close()


def load_latest_scans() -> list[dict]:
    """Her sembol için en son tarama sonucunu, dict listesi olarak döner (DataFrame'e çevrilmeye hazır)."""
    db = SessionLocal()
    try:
        rows = db.query(LynchScanResult).order_by(LynchScanResult.scanned_at.desc()).all()
        latest_by_symbol: dict[str, LynchScanResult] = {}
        for r in rows:
            if r.symbol not in latest_by_symbol:
                latest_by_symbol[r.symbol] = r

        return [
            {
                "symbol": r.symbol, "market": r.market, "company_name": r.company_name,
                "currency": r.currency, "sector": r.sector, "scanned_at": r.scanned_at,
                "category": r.category, "peg": r.peg, "pegy": r.pegy, "pe_ratio": r.pe_ratio,
                "eps_growth_pct": r.eps_growth_pct, "debt_to_equity": r.debt_to_equity,
                "institutional_ownership_pct": r.institutional_ownership_pct,
                "criteria_passed_count": r.criteria_passed_count, "criteria_total": r.criteria_total,
                "criteria_detail": json.loads(r.criteria_detail) if r.criteria_detail else {},
                "recommendation": r.recommendation, "current_price": r.current_price,
                "day_change_pct": r.day_change_pct, "fifty_two_week_low": r.fifty_two_week_low,
                "fifty_two_week_high": r.fifty_two_week_high,
                "position_in_52w_range_pct": r.position_in_52w_range_pct,
                "average_volume": r.average_volume, "market_cap": r.market_cap,
                "price_to_book": r.price_to_book, "return_on_equity_pct": r.return_on_equity_pct,
                "current_ratio": r.current_ratio, "dividend_yield_pct": r.dividend_yield_pct,
                "target_mean_price": r.target_mean_price, "upside_to_target_pct": r.upside_to_target_pct,
                "recommendation_key": r.recommendation_key, "error": r.error,
            }
            for r in latest_by_symbol.values()
        ]
    finally:
        db.close()
