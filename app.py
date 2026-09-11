"""
PEG Radar - Peter Lynch tarzı hisse tarama sitesi (ABD + Türkiye).

Bu uygulama SADECE analiz yapar - hiçbir emir açmaz, hiçbir broker'a
bağlanmaz, hiçbir API anahtarı gerektirmez (yfinance ücretsizdir).
"""
import time

import pandas as pd
import streamlit as st

from cached_fetch import cached_fetch_fundamentals
from config import settings
from database import get_app_settings, init_db, save_app_settings
from lynch_strategy import (
    load_latest_scans,
    persist_scan_result,
    scan_symbol,
)
from scheduler import get_scheduler

st.set_page_config(page_title="PEG Radar", page_icon="🧭", layout="wide")
init_db()

CATEGORY_LABELS = {
    "fast_grower": "Hızlı büyüyen", "stalwart": "Sağlam duran", "slow_grower": "Yavaş büyüyen",
    "cyclical": "Döngüsel", "asset_play": "Varlık oyunu", "turnaround": "Dönüşüm", "unknown": "Belirsiz",
}
CRITERIA_LABELS = {
    "peg_uygun": "PEG oranı uygun (≤1.0)",
    "buyume_surdurulebilir": "Kazanç büyümesi sürdürülebilir bantta",
    "borc_makul": "Borç/özsermaye makul",
    "karli": "Kâr marjı pozitif",
    "buyume_alani_var": "Kurumsal sahiplik büyüme alanı bırakıyor",
}


# --- Basit şifre kapısı (opsiyonel - APP_PASSWORD boşsa devre dışı) ---
def check_password() -> bool:
    if not settings.APP_PASSWORD:
        return True
    if st.session_state.get("authenticated"):
        return True

    st.title("🧭 PEG Radar")
    pwd = st.text_input("Şifre", type="password")
    if st.button("Giriş"):
        if pwd == settings.APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Yanlış şifre.")
    return False


if not check_password():
    st.stop()

# Arka plan zamanlayıcısını (otomatik tarama) başlatıyoruz - st.cache_resource
# sayesinde bu, kaç tarayıcı sekmesi açılırsa açılsın süreç başına SADECE BİR
# kez çalışır. Uygulama sürecinin sürekli açık kalması gerektiğini unutmayın
# (bkz. README) - sadece bir sekme açıkken değil.
get_scheduler()


def run_scan(symbols: list[str]) -> None:
    progress = st.progress(0, text="Tarama başlıyor...")
    status = st.empty()

    for i, symbol in enumerate(symbols):
        status.caption(f"Taranıyor: {symbol} ({i + 1}/{len(symbols)})")
        score = scan_symbol(symbol, fetch_fn=cached_fetch_fundamentals)
        persist_scan_result(score)
        progress.progress((i + 1) / len(symbols), text=f"{i + 1}/{len(symbols)} tamamlandı")

        # Semboller arasına gecikme - Yahoo'nun bot korumasını tetiklememek için.
        # Cache'ten geldiyse zaten ağ isteği yapılmadı, gecikmeye gerek yok.
        if i < len(symbols) - 1:
            time.sleep(settings.LYNCH_REQUEST_DELAY_SECONDS)

    status.empty()
    progress.empty()


# ============================== SIDEBAR ==============================
persisted = get_app_settings()

with st.sidebar:
    st.header("🧭 PEG Radar")
    st.caption("Peter Lynch tarzı sayısal checklist ile ABD ve Türkiye hisse taraması.")

    st.subheader("Otomatik tarama")
    auto_scan_ui = st.toggle("Her borsa kapanışında otomatik tara", value=persisted["auto_scan_enabled"])
    if auto_scan_ui != persisted["auto_scan_enabled"]:
        save_app_settings(auto_scan_enabled=auto_scan_ui)
        st.rerun()

    st.caption(
        f"ABD kapanışı: {settings.US_SCAN_HOUR:02d}:{settings.US_SCAN_MINUTE:02d} "
        f"({settings.US_SCAN_TIMEZONE}) · Türkiye kapanışı: "
        f"{settings.TR_SCAN_HOUR:02d}:{settings.TR_SCAN_MINUTE:02d} ({settings.TR_SCAN_TIMEZONE}) · hafta içi"
    )
    if not auto_scan_ui:
        st.caption("⏸️ Otomatik tarama şu an kapalı - sadece manuel tarama çalışır.")
    st.caption(
        "Zamanlanmış tarama, izleme listesinin **kaydedilmiş** halini kullanır "
        "(aşağıdaki 'Kaydet' butonuyla kaydedin) ve uygulama sürecinin sürekli "
        "açık olmasını gerektirir - detaylar için README."
    )

    st.divider()
    st.subheader("İzleme listesi")
    us_watchlist_raw = st.text_area("ABD (virgülle ayır)", value=persisted["watchlist_us"], height=70)
    tr_watchlist_raw = st.text_area("Türkiye - BIST (virgülle ayır, .IS ekiyle)", value=persisted["watchlist_tr"], height=70)

    if st.button("Kaydet (kalıcı)", use_container_width=True):
        save_app_settings(watchlist_us=us_watchlist_raw, watchlist_tr=tr_watchlist_raw)
        st.success("Kaydedildi. Otomatik tarama artık bu listeyi kullanacak.")

    with st.expander("Checklist eşikleri (ileri düzey)"):
        settings.LYNCH_MAX_PEG = st.slider("Maksimum PEG", 0.1, 3.0, settings.LYNCH_MAX_PEG, 0.1)
        settings.LYNCH_MIN_EPS_GROWTH_PCT = st.slider("Minimum EPS büyümesi (%)", 0, 50, int(settings.LYNCH_MIN_EPS_GROWTH_PCT))
        settings.LYNCH_MAX_EPS_GROWTH_PCT = st.slider("Maksimum EPS büyümesi (%)", 20, 100, int(settings.LYNCH_MAX_EPS_GROWTH_PCT))
        settings.LYNCH_MAX_DEBT_TO_EQUITY = st.slider("Maksimum Borç/Özsermaye", 0.1, 2.0, settings.LYNCH_MAX_DEBT_TO_EQUITY, 0.1)
        settings.LYNCH_MIN_CRITERIA_PASSED = st.slider("Aday için minimum kriter sayısı", 1, 5, settings.LYNCH_MIN_CRITERIA_PASSED)
        st.caption("Bu eşikler hem manuel hem otomatik taramayı hemen etkiler (süreç ayakta kaldığı sürece).")

    with st.expander("Yahoo Finance rate-limit ayarları"):
        settings.LYNCH_REQUEST_DELAY_SECONDS = st.slider("Semboller arası bekleme (sn)", 1.0, 15.0, settings.LYNCH_REQUEST_DELAY_SECONDS, 0.5)
        st.caption("429 hatası alıyorsanız bu değeri artırın. Detaylar için README'ye bakın.")

    st.divider()
    st.subheader("İsteğe bağlı (manuel) tarama")
    us_symbols = [s.strip().upper() for s in us_watchlist_raw.split(",") if s.strip()]
    tr_symbols = [s.strip().upper() for s in tr_watchlist_raw.split(",") if s.strip()]
    all_symbols = us_symbols + tr_symbols

    scan_clicked = st.button(f"Taramayı şimdi çalıştır ({len(all_symbols)} sembol)", type="primary", use_container_width=True)
    st.caption("Yukarıdaki kutulardaki (kaydedilmiş veya kaydedilmemiş) listeyi hemen tarar.")

    st.divider()
    st.caption(
        "⚠️ Bu bir yatırım tavsiyesi değildir. Lynch'in checklist'inin sadece "
        "sayısal kısmını otomatikleştirir; niteliksel değerlendirme (işi "
        "anlamak, hikayeyi doğrulamak) size aittir."
    )


# ============================== TARAMA ==============================
if scan_clicked and all_symbols:
    run_scan(all_symbols)

results = load_latest_scans()

if not results:
    st.title("🧭 PEG Radar")
    st.info("Henüz tarama yapılmadı. Soldaki 'Taramayı çalıştır' butonuna basın.")
    st.stop()

df = pd.DataFrame(results)
df["category_label"] = df["category"].map(CATEGORY_LABELS).fillna(df["category"])


# ============================== ÜST ÖZET ==============================
st.title("🧭 PEG Radar")
st.caption("Peter Lynch'in sayısal checklist'ine göre ABD ve Türkiye borsalarını tarar. Sadece analiz — hiçbir emir açılmaz.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Taranan", len(df))
col2.metric("Aday", int(df["recommendation"].sum()))

us_last = df.loc[df["market"] == "US", "scanned_at"].max() if (df["market"] == "US").any() else None
tr_last = df.loc[df["market"] == "TR", "scanned_at"].max() if (df["market"] == "TR").any() else None
col3.metric("Son ABD taraması", us_last.strftime("%d.%m %H:%M") if pd.notna(us_last) else "—")
col4.metric("Son Türkiye taraması", tr_last.strftime("%d.%m %H:%M") if pd.notna(tr_last) else "—")


# ============================== FİLTRELER ==============================
f1, f2, f3 = st.columns([1, 2, 2])
market_filter = f1.radio("Piyasa", ["Tümü", "ABD", "Türkiye"], horizontal=True)
search = f2.text_input("Sembol veya şirket ara", placeholder="örn. AAPL, Turkcell...")
sort_by = f3.selectbox("Sırala", ["PEG (düşükten yükseğe)", "Kriter sayısı", "Kazanç büyümesi", "Sembol (A-Z)"])

filtered = df.copy()
if market_filter == "ABD":
    filtered = filtered[filtered["market"] == "US"]
elif market_filter == "Türkiye":
    filtered = filtered[filtered["market"] == "TR"]

if search:
    mask = (
        filtered["symbol"].str.contains(search, case=False, na=False)
        | filtered["company_name"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]

sort_map = {
    "PEG (düşükten yükseğe)": ("peg", True),
    "Kriter sayısı": ("criteria_passed_count", False),
    "Kazanç büyümesi": ("eps_growth_pct", False),
    "Sembol (A-Z)": ("symbol", True),
}
sort_col, ascending = sort_map[sort_by]
filtered = filtered.sort_values(sort_col, ascending=ascending, na_position="last")


# ============================== TABLO ==============================
display_df = filtered[[
    "symbol", "market", "company_name", "category_label", "current_price", "currency",
    "peg", "eps_growth_pct", "debt_to_equity", "criteria_passed_count", "recommendation", "error",
]].rename(columns={
    "symbol": "Sembol", "market": "Piyasa", "company_name": "Şirket", "category_label": "Kategori",
    "current_price": "Fiyat", "currency": "Para birimi", "peg": "PEG", "eps_growth_pct": "Büyüme %",
    "debt_to_equity": "Borç/Özsermaye", "criteria_passed_count": "Kriter", "recommendation": "Aday",
    "error": "Hata",
})

# Sayısal kolonları açıkça float'a çeviriyoruz ki eksik değerler (None) boş
# hücre olarak görünsün - aksi halde bazı durumlarda pandas kolonu "object"
# tipinde tutup None'ı literal "None" metni olarak basıyordu.
for col in ["Fiyat", "PEG", "Büyüme %", "Borç/Özsermaye"]:
    display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

# Metin kolonlarında da None yerine boş string - aynı "None" yazısı sorunu.
for col in ["Şirket", "Para birimi", "Hata"]:
    display_df[col] = display_df[col].fillna("")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Fiyat": st.column_config.NumberColumn(format="%.2f"),
        "PEG": st.column_config.NumberColumn(format="%.2f"),
        "Büyüme %": st.column_config.NumberColumn(format="%.1f%%"),
        "Borç/Özsermaye": st.column_config.NumberColumn(format="%.2f"),
        "Kriter": st.column_config.ProgressColumn(min_value=0, max_value=5, format="%d/5"),
        "Aday": st.column_config.CheckboxColumn(),
    },
)


# ============================== DETAY PANELİ ==============================
st.subheader("Hisse detayı")
if len(filtered) == 0:
    st.caption("Filtreye uyan hisse yok.")
else:
    selected_symbol = st.selectbox("Detay için sembol seçin", filtered["symbol"].tolist())
    row = filtered[filtered["symbol"] == selected_symbol].iloc[0]

    if row["error"]:
        st.warning(f"Bu sembol için veri alınamadı: {row['error']}")
    else:
        d1, d2, d3, d4 = st.columns(4)
        change = row["day_change_pct"] or 0
        d1.metric("Fiyat", f"{row['current_price']:.2f} {row['currency'] or ''}", f"{change:+.2f}%")
        d2.metric("PEG / PEGY", f"{row['peg']:.2f}" if pd.notna(row["peg"]) else "—",
                   f"PEGY {row['pegy']:.2f}" if pd.notna(row["pegy"]) else None, delta_color="off")
        d3.metric("F/K oranı", f"{row['pe_ratio']:.1f}" if pd.notna(row["pe_ratio"]) else "—")
        d4.metric("Piyasa değeri", f"{row['market_cap']/1e9:.1f}B" if pd.notna(row["market_cap"]) else "—")

        e1, e2, e3, e4 = st.columns(4)
        e1.metric("ROE", f"{row['return_on_equity_pct']:.1f}%" if pd.notna(row["return_on_equity_pct"]) else "—")
        e2.metric("Cari oran", f"{row['current_ratio']:.2f}" if pd.notna(row["current_ratio"]) else "—")
        e3.metric("Temettü verimi", f"{row['dividend_yield_pct']:.1f}%" if pd.notna(row["dividend_yield_pct"]) else "—")
        e4.metric("Kurumsal sahiplik", f"{row['institutional_ownership_pct']:.0f}%" if pd.notna(row["institutional_ownership_pct"]) else "—")

        if pd.notna(row["fifty_two_week_low"]) and pd.notna(row["fifty_two_week_high"]) and pd.notna(row["position_in_52w_range_pct"]):
            st.caption(f"52 haftalık aralık: {row['fifty_two_week_low']:.2f} — {row['fifty_two_week_high']:.2f}")
            st.progress(min(max(row["position_in_52w_range_pct"] / 100, 0.0), 1.0))

        if pd.notna(row["target_mean_price"]):
            st.caption(f"Analist hedef fiyatı: {row['target_mean_price']:.2f} "
                       f"({row['upside_to_target_pct']:+.1f}%), görüş: {row['recommendation_key'] or '—'}")

        st.markdown("**Checklist**")
        criteria = row["criteria_detail"] or {}
        for key, passed in criteria.items():
            icon = "✅" if passed else "❌"
            st.write(f"{icon} {CRITERIA_LABELS.get(key, key)}")

st.divider()
st.caption(
    "Veri kaynağı: yfinance (Yahoo Finance), gecikmeli. Bu bir yatırım tavsiyesi "
    "değildir — sadece Lynch'in sayısal checklist'ine göre bir ön-eleme filtresidir."
)
