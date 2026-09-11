"""
st.cache_data ile sarılmış fetch_fundamentals. Hem app.py'deki manuel
taramanın hem scheduler.py'deki otomatik taramanın AYNI önbelleği
paylaşması için tek yerde tanımlandı - böylece otomatik tarama biraz
önce manuel taranmış bir sembolü boşuna tekrar Yahoo'dan çekmez.
"""
import streamlit as st

from config import settings
from lynch_strategy import fetch_fundamentals


@st.cache_data(ttl=settings.LYNCH_CACHE_TTL_SECONDS, show_spinner=False)
def cached_fetch_fundamentals(symbol: str) -> dict:
    return fetch_fundamentals(symbol)
