# app/dashboard.py
# VERSIONE DI DEBUG: Mostra i dati grezzi per l'analisi
import streamlit as st
import pandas as pd
import configparser
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data_fetcher import fetch_all_data
from src.indicator_calculator import calculate_signals

st.set_page_config(page_title="Kriterion Quant - Debug", page_icon="🔱", layout="wide")
st.title("🔱 Cruscotto di Copertura - Modalità Debug")

# ... (La sidebar rimane identica, non la riporto per brevità) ...
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


st.header("Generatore di Segnale Giornaliero")

if st.button("Esegui Analisi e Mostra Risultati Grezzi"):
    with st.spinner("Download dati..."):
        fred_series_str = config.get('DATA', 'fred_series_cmi')
        tickers = ['SPY', 'ES=F', '^VIX', '^VIX3M']
        market_data, cmi_data = fetch_all_data(fred_series_str, tickers)
    st.success("Download completato.")

    with st.spinner("Calcolo segnali..."):
        df_signals = calculate_signals(market_data, cmi_data, cmi_window, vix_upper, vix_lower)
    st.success("Calcolo segnali completato.")

    st.markdown("---")
    st.header("🔍 Analisi del DataFrame Calcolato")
    st.warning("Stiamo visualizzando l'output grezzo della funzione di calcolo per trovare la causa dei dati mancanti.")

    # Mostra l'intero DataFrame per il debug
    st.dataframe(df_signals)

    st.subheader("Ultime 15 righe (le più importanti per il debug)")
    st.dataframe(df_signals.tail(15))

    st.subheader("Informazioni sul DataFrame (`.info()`)")
    buffer = pd.io.common.StringIO()
    df_signals.info(buf=buffer)
    s = buffer.getvalue()
    st.text(s)
    
    st.markdown("---")
    st.header("✅ Segnale Finale (dopo pulizia)")

    # Eseguiamo la pulizia qui, per trovare il segnale valido
    final_df = df_signals.dropna(subset=['SPY_Close', 'CMI_MA', 'VIX_Ratio'])

    if final_df.empty:
        st.error("ERRORE DI VALIDAZIONE: Dopo la pulizia, non rimangono segnali validi.")
    else:
        latest_signal = final_df.iloc[-1]
        current_date = latest_signal.name.strftime('%Y-%m-%d')
        st.success(f"Trovato segnale valido per il: {current_date}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Segnale CMI", f"{int(latest_signal['Signal_CMI'])}")
        col2.metric("Segnale VIX Ratio", f"{int(latest_signal['Signal_VIX'])}")
        col3.metric("Tranche di Copertura", f"{int(latest_signal['Signal_Count'])}")
