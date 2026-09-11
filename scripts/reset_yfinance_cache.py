"""
yfinance'in kalıcı çerez/crumb önbelleğini temizler.

KULLANIM:
1. Streamlit uygulamasını tamamen durdurun (terminalde Ctrl+C).
2. python scripts/reset_yfinance_cache.py
3. streamlit run app.py

Detaylar için README.md'deki "Bilinen sorun" bölümüne bakın.
"""
import shutil
from pathlib import Path

import platformdirs


def main():
    cache_dir = Path(platformdirs.user_cache_dir()) / "py-yfinance"

    if not cache_dir.exists():
        print(f"Önbellek klasörü zaten yok: {cache_dir}")
        return

    print(f"Siliniyor: {cache_dir}")
    shutil.rmtree(cache_dir, ignore_errors=True)
    print("Temizlendi." if not cache_dir.exists() else "UYARI: klasör silinemedi.")


if __name__ == "__main__":
    main()
