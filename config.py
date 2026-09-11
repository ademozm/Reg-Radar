"""
PEG Radar - konfigürasyon.

Eski trading_system'e göre kasıtlı olarak çok daha küçük: TRADING_MODE,
broker ayarları, risk parametreleri, kill-switch gibi hiçbir şey yok
çünkü bu sistem artık SADECE tarama/analiz yapıyor.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./peg_radar.db")

    # Boş bırakılırsa şifre sorulmaz (tek kullanıcılık, kendi makinenizde
    # çalıştırıyorsanız buna gerek yoktur). Genel internete açacaksanız set edin.
    APP_PASSWORD: str = os.getenv("APP_PASSWORD", "")

    LYNCH_WATCHLIST_US_DEFAULT: str = os.getenv(
        "LYNCH_WATCHLIST_US", "AAPL,MSFT,COST,TJX,ODFL,NVDA,LULU,CMG"
    )
    LYNCH_WATCHLIST_TR_DEFAULT: str = os.getenv(
        "LYNCH_WATCHLIST_TR", "THYAO.IS,GARAN.IS,ASELS.IS,BIMAS.IS,EREGL.IS,SASA.IS,KCHOL.IS,TUPRS.IS"
    )

    LYNCH_MAX_PEG: float = _float("LYNCH_MAX_PEG", 1.0)
    LYNCH_MIN_EPS_GROWTH_PCT: float = _float("LYNCH_MIN_EPS_GROWTH_PCT", 15.0)
    LYNCH_MAX_EPS_GROWTH_PCT: float = _float("LYNCH_MAX_EPS_GROWTH_PCT", 50.0)
    LYNCH_MAX_DEBT_TO_EQUITY: float = _float("LYNCH_MAX_DEBT_TO_EQUITY", 0.6)
    LYNCH_MAX_INSTITUTIONAL_OWNERSHIP_PCT: float = _float("LYNCH_MAX_INSTITUTIONAL_OWNERSHIP_PCT", 70.0)
    LYNCH_MIN_CRITERIA_PASSED: int = int(os.getenv("LYNCH_MIN_CRITERIA_PASSED", "4"))

    # Yahoo Finance rate-limit önlemleri
    LYNCH_REQUEST_DELAY_SECONDS: float = _float("LYNCH_REQUEST_DELAY_SECONDS", 4.0)
    LYNCH_MAX_RETRIES: int = int(os.getenv("LYNCH_MAX_RETRIES", "3"))
    LYNCH_RETRY_BACKOFF_BASE_SECONDS: float = _float("LYNCH_RETRY_BACKOFF_BASE_SECONDS", 10.0)

    # yfinance sonuçlarını bu kadar saniye önbellekte tut (aynı taramayı
    # tekrar tekrar çalıştırmak Yahoo'ya gereksiz yük bindirmesin diye)
    LYNCH_CACHE_TTL_SECONDS: int = int(os.getenv("LYNCH_CACHE_TTL_SECONDS", "3600"))

    # --- Otomatik (zamanlanmış) tarama ---
    # Uygulama sürecinin SÜREKLİ çalışıyor olması gerekir (bkz. README) -
    # sadece bir tarayıcı sekmesi açıkken değil, arka planda 7/24.
    AUTO_SCAN_ENABLED_DEFAULT: bool = os.getenv("AUTO_SCAN_ENABLED_DEFAULT", "true").lower() == "true"

    # ABD borsası kapanışı: varsayılan 16:15 America/New_York (resmi kapanış 16:00,
    # verinin güncellenmesi için birkaç dakika payı bırakıldı)
    US_SCAN_HOUR: int = int(os.getenv("US_SCAN_HOUR", "16"))
    US_SCAN_MINUTE: int = int(os.getenv("US_SCAN_MINUTE", "15"))
    US_SCAN_TIMEZONE: str = os.getenv("US_SCAN_TIMEZONE", "America/New_York")

    # BIST kapanışı: varsayılan 18:10 Europe/Istanbul (resmi kapanış 18:00)
    TR_SCAN_HOUR: int = int(os.getenv("TR_SCAN_HOUR", "18"))
    TR_SCAN_MINUTE: int = int(os.getenv("TR_SCAN_MINUTE", "10"))
    TR_SCAN_TIMEZONE: str = os.getenv("TR_SCAN_TIMEZONE", "Europe/Istanbul")

    # --- Bildirim (opsiyonel - boşsa devre dışı, sadece log'a yazılır) ---
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")


settings = Settings()
