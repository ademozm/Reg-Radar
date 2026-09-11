"""
Otomatik tarama tamamlandığında özet bildirim gönderir.

Telegram (varsa) + her zaman log. Token/chat_id boşsa Telegram'a hiç
istek atılmaz, sadece log'a yazılır - bildirim kurmak zorunlu değildir,
uygulama onsuz da tam çalışır, sadece sessiz kalır.
"""
import logging

from config import settings

logger = logging.getLogger(__name__)


def build_scan_summary_message(market_label: str, scores: list) -> str:
    """
    Saf fonksiyon: bir LynchScore listesinden okunabilir bir özet metni
    üretir. Ağ/DB'ye dokunmaz - bu yüzden ağsız test edilebilir.
    """
    total = len(scores)
    errors = [s for s in scores if s.error]
    candidates = [s for s in scores if s.recommendation]

    lines = [f"📡 PEG Radar - {market_label} taraması tamamlandı"]
    lines.append(f"{total} hisse tarandı, {len(candidates)} aday bulundu.")

    if candidates:
        lines.append("")
        lines.append("Adaylar:")
        for s in sorted(candidates, key=lambda s: (s.peg is None, s.peg)):
            peg_str = f"{s.peg:.2f}" if s.peg is not None else "—"
            lines.append(f"  • {s.symbol} — PEG {peg_str}, kriter {s.criteria_passed_count}/{s.criteria_total}")

    if errors:
        lines.append("")
        lines.append(f"⚠️ {len(errors)} sembol için veri alınamadı: {', '.join(e.symbol for e in errors)}")

    return "\n".join(lines)


def notify(message: str) -> None:
    logger.info("Bildirim: %s", message.replace("\n", " | "))

    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return

    try:
        import requests
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception:
        logger.exception("Telegram bildirimi gönderilemedi")
