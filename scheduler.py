"""
Arka plan zamanlayıcısı: her iş günü, ilgili borsanın kapanışından kısa
süre sonra otomatik tarama yapar ve sonucu bildirir.

ÖNEMLİ MİMARİ NOT: Streamlit'in kendi başına bir cron/zamanlayıcı özelliği
yok. Burada kullanılan APScheduler, Streamlit'in çalıştığı Python süreci
İÇİNDE ayrı bir arka plan thread'i olarak çalışıyor. Bu şu anlama gelir:

  - Uygulama süreci (streamlit run app.py) SÜREKLİ açık kalmalıdır.
    Sadece bir tarayıcı sekmesi açıkken değil - süreç arka planda da
    çalışıyor olsa yeterlidir (örn. bir sunucuda / Docker'da / systemd
    servisi olarak).
  - Streamlit Community Cloud gibi "kullanılmayınca uyuyan" platformlarda
    bu zamanlayıcı GÜVENİLİR ÇALIŞMAZ - uygulama uykudayken hiçbir kod
    çalışmaz, dolayısıyla borsa kapanışı saatinde kimse siteyi açmamışsa
    otomatik tarama tetiklenmeyebilir. Günlük otomatik taramaya
    güvenecekseniz, bu uygulamayı 7/24 açık bir sunucuda/VPS'te veya
    kendi bilgisayarınızda sürekli çalışır halde tutmanız gerekir.
  - Resmi piyasa tatilleri hesaba katılmıyor (sadece hafta içi mi diye
    bakılıyor) - tatil günlerinde tarama yine de çalışır, muhtemelen
    bir önceki günün verisiyle veya hatalı sonuçla karşılaşırsınız,
    zararsızdır ama beklenmedik değildir.
"""
import logging
import time

import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from cached_fetch import cached_fetch_fundamentals
from config import settings
from database import get_app_settings, mark_notification_sent
from lynch_strategy import persist_scan_result, scan_symbol
from notifications import build_scan_summary_message, notify

logger = logging.getLogger(__name__)


def _run_scan_for_market(market_label: str, symbols: list[str], notify_key: str) -> None:
    app_settings = get_app_settings()
    if not app_settings["auto_scan_enabled"]:
        logger.info("Otomatik tarama kapalı (auto_scan_enabled=False), %s taraması atlandı", market_label)
        return

    if not symbols:
        logger.info("%s için izleme listesi boş, tarama atlandı", market_label)
        return

    logger.info("Otomatik %s taraması başlıyor: %s", market_label, symbols)
    scores = []
    for i, symbol in enumerate(symbols):
        score = scan_symbol(symbol, fetch_fn=cached_fetch_fundamentals)
        persist_scan_result(score)
        scores.append(score)
        if i < len(symbols) - 1:
            time.sleep(settings.LYNCH_REQUEST_DELAY_SECONDS)

    message = build_scan_summary_message(market_label, scores)
    notify(message)
    mark_notification_sent(notify_key)
    logger.info("Otomatik %s taraması tamamlandı: %d hisse, %d aday",
                market_label, len(scores), sum(1 for s in scores if s.recommendation))


def scheduled_us_scan() -> None:
    app_settings = get_app_settings()
    symbols = [s.strip().upper() for s in (app_settings["watchlist_us"] or "").split(",") if s.strip()]
    _run_scan_for_market("ABD", symbols, notify_key="US")


def scheduled_tr_scan() -> None:
    app_settings = get_app_settings()
    symbols = [s.strip().upper() for s in (app_settings["watchlist_tr"] or "").split(",") if s.strip()]
    _run_scan_for_market("Türkiye", symbols, notify_key="TR")


@st.cache_resource(show_spinner=False)
def get_scheduler() -> BackgroundScheduler:
    """
    Zamanlayıcıyı bir kez oluşturup başlatır. st.cache_resource sayesinde
    kaç tarayıcı sekmesi/oturumu açılırsa açılsın, bu fonksiyonun gövdesi
    Python süreci başına SADECE BİR KEZ çalışır - yani iki job'ın iki kere
    eklenip taramanın iki kere tetiklenmesi gibi bir sorun olmaz.
    """
    scheduler = BackgroundScheduler(timezone="UTC")

    scheduler.add_job(
        scheduled_us_scan,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=settings.US_SCAN_HOUR,
            minute=settings.US_SCAN_MINUTE,
            timezone=settings.US_SCAN_TIMEZONE,
        ),
        id="us_market_close_scan",
        replace_existing=True,
    )
    scheduler.add_job(
        scheduled_tr_scan,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=settings.TR_SCAN_HOUR,
            minute=settings.TR_SCAN_MINUTE,
            timezone=settings.TR_SCAN_TIMEZONE,
        ),
        id="tr_market_close_scan",
        replace_existing=True,
    )
    scheduler.start()

    logger.info(
        "Zamanlayıcı başladı: ABD %02d:%02d %s, Türkiye %02d:%02d %s (hafta içi)",
        settings.US_SCAN_HOUR, settings.US_SCAN_MINUTE, settings.US_SCAN_TIMEZONE,
        settings.TR_SCAN_HOUR, settings.TR_SCAN_MINUTE, settings.TR_SCAN_TIMEZONE,
    )
    return scheduler
