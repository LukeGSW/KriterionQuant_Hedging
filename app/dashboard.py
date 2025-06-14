# app/dashboard.py

import streamlit as st
import pandas as pd
import configparser
import sys
import os

# Aggiunge la cartella 'src' al path per permettere l'import dei moduli
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_fetcher import fetch_all_data
from src.indicator_calculator import calculate_signals

# --- Configurazione della Pagina ---
st.set_page_config(
    page_title="Kriterion Quant - Cruscotto di Copertura",
    page_icon="🔱",
    layout="wide"
)

st.title("🔱 Cruscotto di Copertura Kriterion Quant")
st.markdown("Interfaccia per monitorare i segnali di copertura della strategia composita.")

# --- Caricamento Configurazione ---
config = configparser.ConfigParser()
# Il path deve essere relativo alla posizione di esecuzione dello script
config.read('config.ini')

# --- Sidebar per i Parametri ---
st.sidebar.header("Parametri della Strategia")

# Sezione Parametri di base
st.sidebar.subheader("Trading")
capitale = config.getfloat('STRATEGY_PARAMS', 'capitale_iniziale')
hedge_perc = config.getfloat('STRATEGY_PARAMS', 'hedge_percentage_per_tranche')
st.sidebar.metric("Capitale Iniziale", f"€ {capitale:,.2f}")
st.sidebar.metric("Hedge per Tranche", f"{hedge_perc:.1%}")

# Sezione CMI
st.sidebar.subheader("Indicatore CMI vs MA")
cmi_window = config.getint('STRATEGY_PARAMS', 'cmi_ma_window')
st.sidebar.metric("Finestra Media Mobile CMI", f"{cmi_window} giorni")

# Sezione VIX Ratio
st.sidebar.subheader("Indicatore VIX Ratio")
vix_upper = config.getfloat('STRATEGY_PARAMS', 'vix_ratio_upper_threshold')
vix_lower = config.getfloat('STRATEGY_PARAMS', 'vix_ratio_lower_threshold')
st.sidebar.metric("Soglia Superiore VIX", f"{vix_upper}")
st.sidebar.metric("Soglia Inferiore VIX", f"{vix_lower}")

st.sidebar.info("Nota: Per ora, i parametri sono letti da `config.ini`. L'interattività per modificarli verrà aggiunta in seguito.")


# --- Pannello Principale ---
st.header("Generatore di Segnale Giornaliero")

if st.button("Esegui Analisi e Genera Segnale"):
    
    with st.spinner("Download dei dati in corso..."):
        fred_series_str = config.get('DATA', 'fred_series_cmi')
        tickers = ['SPY', 'ES=F', '^VIX', '^VIX3M']
        market_data, cmi_data = fetch_all_data(fred_series_str, tickers)
    
    if market_data is not None and cmi_data is not None:
        st.success("Download dati completato.")
        
        with st.spinner("Calcolo degli indicatori e dei segnali..."):
            df_signals = calculate_signals(
                market_data, cmi_data, cmi_window, vix_upper, vix_lower
            )
        st.success("Calcolo segnali completato.")

        # Estrai e mostra l'ultimo segnale
        latest_signal = df_signals.iloc[-1]
        current_date = latest_signal.name.strftime('%Y-%m-%d')

        st.subheader(f"Segnale calcolato per il: {current_date}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Segnale CMI", f"{int(latest_signal['Signal_CMI'])}")
        col2.metric("Segnale VIX Ratio", f"{int(latest_signal['Signal_VIX'])}")
        col3.metric("Tranche di Copertura", f"{int(latest_signal['Signal_Count'])}")
        
        # Mostra i valori degli indicatori che hanno generato il segnale
        st.subheader("Valori Chiave degli Indicatori")
        col_a, col_b = st.columns(2)
        col_a.metric("CMI Z-Score", f"{latest_signal['CMI_ZScore']:.3f}")
        col_a.metric("CMI Media Mobile", f"{latest_signal['CMI_MA']:.3f}")
        col_b.metric("VIX Ratio", f"{latest_signal['VIX_Ratio']:.3f}")

        # Mostra grafici per contesto
        st.subheader("Grafici degli Indicatori")
        
        st.write("Andamento CMI vs Media Mobile")
        st.line_chart(df_signals[['CMI_ZScore', 'CMI_MA']].tail(252))
        
        st.write("Andamento VIX Ratio e Soglie")
        chart_data = df_signals[['VIX_Ratio']].tail(252)
        chart_data['Soglia Superiore'] = vix_upper
        chart_data['Soglia Inferiore'] = vix_lower
        st.line_chart(chart_data)
        
        st.subheader("Tabella Dati Recenti")
        st.dataframe(df_signals.tail(10))

    else:
        st.error("Esecuzione fallita. Controllare i log per errori nel download dei dati.")
