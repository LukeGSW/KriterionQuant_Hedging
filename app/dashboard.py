# app/dashboard.py
import streamlit as st
import pandas as pd
import configparser
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.data_fetcher import fetch_all_data
from src.indicator_calculator import calculate_signals_from_notebook
from src.backtester import run_backtest_from_notebook
from src.metrics_calculator import calculate_metrics_from_notebook

# ... (Configurazione pagina e sidebar rimangono invariate) ...
st.set_page_config(page_title="Kriterion Quant - Cruscotto", page_icon="🔱", layout="wide")
st.title("🔱 Cruscotto di Copertura Kriterion Quant")
st.markdown("Interfaccia per monitorare i segnali di copertura e validare la performance storica.")

config = configparser.ConfigParser()
config.read('config.ini')

st.sidebar.header("Parametri della Strategia")
params_dict = dict(config['STRATEGY_PARAMS'])
for key, value in params_dict.items():
    try:
        params_dict[key] = float(value)
    except ValueError:
        pass
st.sidebar.json(params_dict)


# --- SEZIONE BACKTEST STORICO ---
with st.expander("Visualizza Backtest Storico completo (dal 2007)", expanded=True):
    if st.button("Avvia Backtest Storico (Logica Originale)"):
        with st.spinner("Esecuzione in corso..."):
            # 1. Download dati
            fred_series_str = config.get('DATA', 'fred_series_cmi')
            all_tickers = ['SPY', 'ES=F', '^VIX', '^VIX3M']
            market_data_hist, cmi_data_hist = fetch_all_data(config, all_tickers, start_date_str='2007-01-01')

            # 2. Calcolo segnali
            df_signals_hist = calculate_signals_from_notebook(market_data_hist, cmi_data_hist, params_dict)

            # 3. Esecuzione backtest
            equity_curves, strategy_returns, benchmark_returns, trades = run_backtest_from_notebook(df_signals_hist.copy(), params_dict)

            # 4. Calcolo metriche
            strategy_metrics = calculate_metrics_from_notebook(strategy_returns, trades)
            benchmark_metrics = calculate_metrics_from_notebook(benchmark_returns, 0)
            metrics_df = pd.DataFrame({'Strategia': strategy_metrics, 'Benchmark (SPY)': benchmark_metrics})
            
            # 5. Visualizzazione
            st.subheader("Equity Line Storica")
            st.line_chart(equity_curves)
            st.subheader("Metriche di Performance")
            st.table(metrics_df)
