# app/dashboard.py
# VERSIONE FINALE DI DEBUG: Analizza le fonti dati
import streamlit as st
import pandas as pd
import configparser
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data_fetcher import fetch_all_data
# Non importiamo più calculate_signals qui per ora, per isolare il problema

st.set_page_config(page_title="Kriterion Quant - Analisi Fonti", page_icon="🔬", layout="wide")
st.title("🔬 Analizzatore Fonti Dati")

# ... (La sidebar rimane identica) ...
config = configparser.ConfigParser()
config.read('config.ini')
st.sidebar.header("Parametri della Strategia")
st.sidebar.subheader("Trading")
capitale = config.getfloat('STRATEGY_PARAMS', 'capitale_iniziale')
hedge_perc = config.getfloat('STRATEGY_PARAMS', 'hedge_percentage_per_tranche')
st.sidebar.metric("Capitale Iniziale", f"€ {capitale:,.2f}")
st.sidebar.metric("Hedge per Tranche", f"{hedge_perc:.1%}")
st.sidebar.subheader("Indicatore CMI vs MA")
cmi_window = config.getint('STRATEGY_PARAMS', 'cmi_ma_window')
st.sidebar.metric("Finestra Media Mobile CMI", f"{cmi_window} giorni")
st.sidebar.subheader("Indicatore VIX Ratio")
vix_upper = config.getfloat('STRATEGY_PARAMS', 'vix_ratio_upper_threshold')
vix_lower = config.getfloat('STRATEGY_PARAMS', 'vix_ratio_lower_threshold')
st.sidebar.metric("Soglia Superiore VIX", f"{vix_upper}")
st.sidebar.metric("Soglia Inferiore VIX", f"{vix_lower}")


st.header("Test di Download Dati")

if st.button("Esegui Download e Analizza Fonti"):
    with st.spinner("Download dati in corso..."):
        fred_series_str = config.get('DATA', 'fred_series_cmi')
        tickers = ['SPY', 'ES=F', '^VIX', '^VIX3M']
        market_data, cmi_data = fetch_all_data(fred_series_str, tickers)
    st.success("Test di download completato.")

    st.markdown("---")
    st.subheader("Analisi `market_data` (da Yahoo Finance)")
    if market_data.empty:
        st.error("RISULTATO: Il DataFrame `market_data` è VUOTO.")
    else:
        st.success("RISULTATO: Il DataFrame `market_data` CONTIENE DATI.")
        st.write("Ultime 5 righe:")
        st.dataframe(market_data.tail())
        buffer = pd.io.common.StringIO()
        market_data.info(buf=buffer)
        s = buffer.getvalue()
        st.text(s)

    st.markdown("---")
    st.subheader("Analisi `cmi_data` (da FRED)")
    if cmi_data.empty:
        st.error("RISULTATO: Il DataFrame `cmi_data` è VUOTO.")
    else:
        st.success("RISULTATO: Il DataFrame `cmi_data` CONTIENE DATI.")
        st.write("Ultime 5 righe:")
        st.dataframe(cmi_data.tail())
        buffer = pd.io.common.StringIO()
        cmi_data.info(buf=buffer)
        s = buffer.getvalue()
        st.text(s)
