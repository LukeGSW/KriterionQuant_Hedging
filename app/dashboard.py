# app/dashboard.py
import streamlit as st
import pandas as pd
import configparser
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data_fetcher import fetch_all_data
from src.indicator_calculator import calculate_signals

st.set_page_config(page_title="Kriterion Quant - Cruscotto", page_icon="🔱", layout="wide")
st.title("🔱 Cruscotto di Copertura Kriterion Quant")
st.markdown("Interfaccia per monitorare i segnali di copertura della strategia composita.")

config = configparser.ConfigParser()
config.read('config.ini')

# --- Sidebar ---
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


# --- Pannello Principale ---
st.header("Generatore di Segnale Giornaliero")

if st.button("Esegui Analisi e Genera Segnale"):
    with st.spinner("Download dati..."):
        fred_series_str = config.get('DATA', 'fred_series_cmi')
        tickers = ['SPY', 'ES=F', '^VIX', '^VIX3M']
        market_data, cmi_data = fetch_all_data(fred_series_str, tickers)
    st.success("Download dati completato.")

    with st.spinner("Calcolo segnali..."):
        df_signals = calculate_signals(market_data, cmi_data, cmi_window, vix_upper, vix_lower)
    st.success("Calcolo segnali completato.")

    if df_signals.empty:
        st.warning("Calcolo completato, ma nessun segnale valido generato per l'intervallo di date corrente.")
    else:
        latest_signal = df_signals.iloc[-1]
        current_date = latest_signal.name.strftime('%Y-%m-%d')

        st.subheader(f"Segnale calcolato per il: {current_date}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Segnale CMI", f"{int(latest_signal['Signal_CMI'])}")
        col2.metric("Segnale VIX Ratio", f"{int(latest_signal['Signal_VIX'])}")
        col3.metric("Tranche di Copertura", f"{int(latest_signal['Signal_Count'])}")
        
        st.subheader("Tabella Dati Recenti")
        st.dataframe(df_signals.tail(10))
