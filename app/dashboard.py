# app/dashboard.py
import streamlit as st
import pandas as pd
import configparser
import sys
import os

# Aggiunta dei path e import dei moduli
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data_fetcher import fetch_all_data
from src.indicator_calculator import calculate_signals
from src.backtester import run_historical_backtest # Importa la nuova funzione

# Configurazione della pagina
st.set_page_config(page_title="Kriterion Quant - Cruscotto", page_icon="🔱", layout="wide")
st.title("🔱 Cruscotto di Copertura Kriterion Quant")
st.markdown("Interfaccia per monitorare i segnali di copertura e validare la performance storica.")

# Caricamento della configurazione
config = configparser.ConfigParser()
config.read('config.ini')

# --- Sidebar ---
st.sidebar.header("Parametri della Strategia")
params_dict = dict(config['STRATEGY_PARAMS'])
for key, value in params_dict.items():
    try:
        params_dict[key] = float(value)
    except ValueError:
        pass # Mantieni come stringa se non è un numero
st.sidebar.json(params_dict)


# --- SEZIONE 1: Generatore di Segnale Giornaliero ---
with st.container(border=True):
    st.header("1. Generatore di Segnale del Giorno")
    if st.button("Esegui Analisi e Genera Segnale Odierno"):
        with st.spinner("Download dati recenti..."):
            fred_series_str = config.get('DATA', 'fred_series_cmi')
            tickers = ['SPY', '^VIX', '^VIX3M']
            market_data, cmi_data = fetch_all_data(fred_series_str, tickers)
        st.success("Download dati completato.")

        with st.spinner("Calcolo segnale..."):
            df_signals = calculate_signals(market_data, cmi_data, 
                                           params_dict['cmi_ma_window'], 
                                           params_dict['vix_ratio_upper_threshold'], 
                                           params_dict['vix_ratio_lower_threshold'])
        st.success("Calcolo segnali completato.")

        if df_signals.empty:
            st.warning("Nessun segnale valido generato per l'intervallo di date corrente.")
        else:
            latest_signal = df_signals.iloc[-1]
            current_date = latest_signal.name.strftime('%Y-%m-%d')
            st.subheader(f"Segnale Calcolato per il: {current_date}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Segnale CMI", f"{int(latest_signal['Signal_CMI'])}")
            col2.metric("Segnale VIX Ratio", f"{int(latest_signal['Signal_VIX'])}")
            col3.metric("Tranche di Copertura", f"{int(latest_signal['Signal_Count'])}")


# --- SEZIONE 2: Backtest Storico ---
with st.expander("Expand per visualizzare il Backtest Storico completo (dal 2007)"):
    st.header("2. Analisi Storica e Metriche")
    if st.button("Avvia Backtest Storico Completo"):
        with st.spinner("Esecuzione in corso... Il backtest completo dal 2007 potrebbe richiedere 1-2 minuti."):
            # 1. Download dati storici completi
            st.info("Passo 1/4: Download dati storici dal 2007...")
            fred_series_str = config.get('DATA', 'fred_series_cmi')
            tickers = ['SPY', '^VIX', '^VIX3M']
            market_data_hist, cmi_data_hist = fetch_all_data(fred_series_str, tickers) # Assumendo che fetch_all_data sia adattabile per date storiche
            
            # 2. Calcolo dei segnali su tutto lo storico
            st.info("Passo 2/4: Calcolo dei segnali storici...")
            df_signals_hist = calculate_signals(market_data_hist, cmi_data_hist, 
                                                params_dict['cmi_ma_window'], 
                                                params_dict['vix_ratio_upper_threshold'], 
                                                params_dict['vix_ratio_lower_threshold'])

            # 3. Esecuzione del backtest
            st.info("Passo 3/4: Esecuzione del backtest sulla base dei segnali...")
            equity_curves, metrics = run_historical_backtest(df_signals_hist.copy(), params_dict)
            
            # 4. Visualizzazione risultati
            st.info("Passo 4/4: Visualizzazione dei risultati.")
            
            st.subheader("Equity Line Storica")
            st.line_chart(equity_curves)
            
            st.subheader("Metriche di Performance")
            metrics_df = pd.DataFrame.from_dict(metrics, orient='index', columns=['Valore'])
            st.table(metrics_df)
