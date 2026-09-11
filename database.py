"""
PEG Radar - veritabanı.

Eski trading_system'deki 6 tablo (Signal, Order, Position, DailyPnL,
AuditLog, LynchScanResult) yerine sadece TEK tablo var: tarama sonuçları.
Trade yapılmadığı için emir/pozisyon/PnL kavramlarının hiçbiri gerekmiyor.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class LynchScanResult(Base):
    __tablename__ = "lynch_scan_results"

    id = Column(String, primary_key=True, default=_uuid)
    scanned_at = Column(DateTime, default=_utcnow)
    symbol = Column(String, nullable=False)
    market = Column(String, nullable=True)             # "US" | "TR"
    company_name = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    category = Column(String, nullable=True)

    peg = Column(Float, nullable=True)
    pegy = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    eps_growth_pct = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    institutional_ownership_pct = Column(Float, nullable=True)
    criteria_passed_count = Column(Integer, default=0)
    criteria_total = Column(Integer, default=0)
    criteria_detail = Column(Text)
    recommendation = Column(Boolean, default=False)

    current_price = Column(Float, nullable=True)
    day_change_pct = Column(Float, nullable=True)
    fifty_two_week_low = Column(Float, nullable=True)
    fifty_two_week_high = Column(Float, nullable=True)
    position_in_52w_range_pct = Column(Float, nullable=True)
    average_volume = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    price_to_book = Column(Float, nullable=True)
    return_on_equity_pct = Column(Float, nullable=True)
    current_ratio = Column(Float, nullable=True)
    dividend_yield_pct = Column(Float, nullable=True)
    target_mean_price = Column(Float, nullable=True)
    upside_to_target_pct = Column(Float, nullable=True)
    recommendation_key = Column(String, nullable=True)

    error = Column(String, nullable=True)


class AppSettingsRow(Base):
    """
    Tek satırlık kalıcı ayar tablosu. Sidebar'daki watchlist ve otomatik
    tarama anahtarı buraya kaydedilir ki hem tarayıcı oturumları arasında
    hem de sunucu yeniden başlasa bile kalıcı olsun - otomatik (zamanlanmış)
    tarama, hiçbir tarayıcı sekmesi açık olmasa bile bu tabloyu okur.
    """
    __tablename__ = "app_settings"

    id = Column(String, primary_key=True, default=lambda: "singleton")
    watchlist_us = Column(Text, nullable=True)
    watchlist_tr = Column(Text, nullable=True)
    auto_scan_enabled = Column(Boolean, default=True)
    last_us_notification_at = Column(DateTime, nullable=True)
    last_tr_notification_at = Column(DateTime, nullable=True)


def get_app_settings() -> dict:
    """Kalıcı ayarları döner; hiç kaydedilmemişse .env varsayılanlarıyla bir satır oluşturur."""
    from config import settings as cfg

    db = SessionLocal()
    try:
        row = db.query(AppSettingsRow).filter(AppSettingsRow.id == "singleton").first()
        if row is None:
            row = AppSettingsRow(
                id="singleton",
                watchlist_us=cfg.LYNCH_WATCHLIST_US_DEFAULT,
                watchlist_tr=cfg.LYNCH_WATCHLIST_TR_DEFAULT,
                auto_scan_enabled=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        return {
            "watchlist_us": row.watchlist_us,
            "watchlist_tr": row.watchlist_tr,
            "auto_scan_enabled": row.auto_scan_enabled,
        }
    finally:
        db.close()


def save_app_settings(watchlist_us: str | None = None, watchlist_tr: str | None = None,
                       auto_scan_enabled: bool | None = None) -> None:
    """Verilenleri kalıcı olarak günceller; None geçilen alanlara dokunmaz."""
    db = SessionLocal()
    try:
        row = db.query(AppSettingsRow).filter(AppSettingsRow.id == "singleton").first()
        if row is None:
            row = AppSettingsRow(id="singleton")
            db.add(row)

        if watchlist_us is not None:
            row.watchlist_us = watchlist_us
        if watchlist_tr is not None:
            row.watchlist_tr = watchlist_tr
        if auto_scan_enabled is not None:
            row.auto_scan_enabled = auto_scan_enabled
        db.commit()
    finally:
        db.close()


def mark_notification_sent(market: str) -> None:
    db = SessionLocal()
    try:
        row = db.query(AppSettingsRow).filter(AppSettingsRow.id == "singleton").first()
        if row is None:
            return
        if market == "US":
            row.last_us_notification_at = _utcnow()
        elif market == "TR":
            row.last_tr_notification_at = _utcnow()
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
