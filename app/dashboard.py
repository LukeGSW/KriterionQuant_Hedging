# app/dashboard.py
# VERSIONE FINALE E UNIFICATA - Tutta la logica in un unico posto
import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_datareader.data as web
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import zscore

# ==============================================================================
# FUNZIONE UNICA CHE CONTIENE TUTTA LA STRATEGIA DAL NOTEBOOK
# ==============================================================================
def run_full_strategy_from_notebook(params):
    
    # --------------------------------------------------------------------------
    # STEP 1: PARAMETRI E DOWNLOAD DATI
    # --------------------------------------------------------------------------
    print("--- Inizio Esecuzione: Download Dati ---")
    CAPITALE_INIZIALE = params['capitale_iniziale']
    
    all_tickers = ['SPY', 'ES=F', '^VIX', '^VIX3M']
    fred_series_cmi = {'TED_Spread': 'TEDRATE', 'Yield_Curve_10Y2Y': 'T10Y2Y', 'VIX': 'VIXCLS', 'High_Yield_Spread': 'BAMLH0A0HYM2'}
    start_date = pd.to_datetime('2007-01-01')
    end_date = pd.to_datetime('today').normalize()

    market_data = yf.download(all_tickers, start=start_date, end=end_date, progress=False, auto_adjust=False)
    cmi_data_dict = {}
    try:
        for name, ticker in fred_series_cmi.items():
            cmi_data_dict[name] = web.DataReader(ticker, 'fred', start_date, end_date)
        cmi_data = pd.concat(cmi_data_dict.values(), axis=1, sort=False).ffill()
        cmi_data.columns = fred_series_cmi.keys()
        # Rimuoviamo il TED Spread se la colonna è vuota, per evitare errori
        if 'TED_Spread' in cmi_data.columns and cmi_data['TED_Spread'].isnull().all():
            print("ATTENZIONE: Dati per TED_Spread non disponibili. L'indicatore viene escluso dal CMI.")
            cmi_data.drop(columns=['TED_Spread'], inplace=True)
            
    except Exception as e:
        st.error(f"Errore nel download dei dati da FRED: {e}")
        return None, None, None, None

    # --------------------------------------------------------------------------
    # STEP 2: CALCOLO SEGNALI
    # --------------------------------------------------------------------------
    print("--- Calcolo Segnali ---")
    data_df = pd.DataFrame({
        'SPY_Close': market_data[('Close', 'SPY')], 'SPY_Open': market_data[('Open', 'SPY')],
        'ES_Close': market_data[('Close', 'ES=F')], 'ES_Open': market_data[('Open', 'ES=F')],
        'VIX_Close': market_data[('Close', '^VIX')], 'VIX3M_Close': market_data[('Close', '^VIX3M')]
    })

    cmi_data_zscore = cmi_data.apply(zscore).dropna()
    if 'Yield_Curve_10Y2Y' in cmi_data_zscore.columns:
        cmi_data_zscore['Yield_Curve_10Y2Y'] = cmi_data_zscore['Yield_Curve_10Y2Y'] * -1
        
    composite_index_zscore = cmi_data_zscore.mean(axis=1)
    cmi_ma = composite_index_zscore.rolling(window=int(params['cmi_ma_window'])).mean()

    data_df['CMI_ZScore'] = composite_index_zscore
    data_df['CMI_MA'] = cmi_ma
    
    # Dropna robusto, solo sulle colonne necessarie per i segnali
    data_df.dropna(subset=['SPY_Open', 'SPY_Close', 'ES_Open', 'ES_Close', 'VIX_Close', 'VIX3M_Close', 'CMI_MA'], inplace=True)
    
    if data_df.empty:
        st.error("Il DataFrame è diventato vuoto dopo la pulizia dei dati. Impossibile continuare.")
        return None, None, None, None

    data_df['Signal_CMI'] = np.where(data_df['CMI_ZScore'] > data_df['CMI_MA'], 1, 0)
    
    data_df['VIX_Ratio'] = data_df['VIX_Close'] / data_df['VIX3M_Close']
    signal_vix = [0] * len(data_df)
    in_hedge_signal = False
    for i in range(len(data_df)):
        ratio = data_df['VIX_Ratio'].iloc[i]
        if ratio > params['vix_ratio_upper_threshold']: in_hedge_signal = True
        elif ratio < params['vix_ratio_lower_threshold']: in_hedge_signal = False
        if in_hedge_signal: signal_vix[i] = 1
    data_df['Signal_VIX'] = signal_vix
    data_df['Signal_Count'] = data_df['Signal_CMI'] + data_df['Signal_VIX']

    # --------------------------------------------------------------------------
    # STEP 3: ESECUZIONE BACKTEST
    # --------------------------------------------------------------------------
    print("--- Esecuzione Backtest ---")
    # Questa è la logica 1:1 del tuo notebook
    initial_spy_price = data_df['SPY_Open'].iloc[0]
    spy_shares = CAPITALE_INIZIALE / initial_spy_price
    cash_from_hedging = 0.0
    es_contracts, hedge_entry_price, current_tranches = 0, 0, 0
    portfolio_history = [{'Date': data_df.index[0], 'Portfolio_Value': CAPITALE_INIZIALE}]
    hedge_trades_count = 0
    hedge_stopped_out = False

    for i in range(len(data_df) - 1):
        target_tranches = data_df['Signal_Count'].iloc[i]
        date_T1, open_spy_T1, open_es_T1, close_spy_T1, close_es_T1 = \
            data_df.index[i+1], data_df['SPY_Open'].iloc[i+1], data_df['ES_Open'].iloc[i+1], \
            data_df['SPY_Close'].iloc[i+1], data_df['ES_Close'].iloc[i+1]
        
        realized_hedge_pnl_today = 0
        
        if current_tranches > 0:
            if open_es_T1 > hedge_entry_price * (1 + params['stop_loss_threshold_hedge']):
                realized_hedge_pnl_today = es_contracts * (open_es_T1 - hedge_entry_price) * params['micro_es_multiplier']
                es_contracts, current_tranches, hedge_stopped_out = 0, 0, True
            elif target_tranches < current_tranches:
                contracts_per_tranche = es_contracts / current_tranches
                contracts_to_close = contracts_per_tranche * (current_tranches - target_tranches)
                realized_hedge_pnl_today = contracts_to_close * (open_es_T1 - hedge_entry_price) * params['micro_es_multiplier']
                es_contracts -= contracts_to_close
                current_tranches = target_tranches

        if target_tranches == 0: hedge_stopped_out = False
            
        if target_tranches > current_tranches and not hedge_stopped_out:
            tranches_to_add = target_tranches - current_tranches
            portfolio_value_at_entry = (spy_shares * open_spy_T1) + cash_from_hedging
            notional_per_tranche = portfolio_value_at_entry * params['hedge_percentage_per_tranche']
            if current_tranches == 0:
                hedge_entry_price = open_es_T1
                hedge_trades_count += 1
            contracts_to_add = - (notional_per_tranche / (open_es_T1 * params['micro_es_multiplier'])) * tranches_to_add
            es_contracts += contracts_to_add
            current_tranches = target_tranches

        cash_from_hedging += realized_hedge_pnl_today
        spy_position_value = spy_shares * close_spy_T1
        unrealized_hedge_pnl = es_contracts * (close_es_T1 - hedge_entry_price) * params['micro_es_multiplier'] if current_tranches > 0 else 0
        portfolio_value = spy_position_value + cash_from_hedging + unrealized_hedge_pnl
        portfolio_history.append({'Date': date_T1, 'Portfolio_Value': portfolio_value})
        
    results_df_final = pd.DataFrame(portfolio_history).set_index('Date')
    results_df_final['Strategy_Returns'] = results_df_final['Portfolio_Value'].pct_change()
    
    benchmark_returns = data_df['SPY_Close'].pct_change()
    cumulative_benchmark = (1 + benchmark_returns).cumprod() * CAPITALE_INIZIALE
    cumulative_benchmark.iloc[0] = CAPITALE_INIZIALE
    
    equity_curves = pd.DataFrame({
        'Strategy_Equity': results_df_final['Portfolio_Value'],
        'Buy_And_Hold_Equity': cumulative_benchmark
    }).dropna()

    return equity_curves, results_df_final['Strategy_Returns'].dropna(), benchmark_returns.dropna(), hedge_trades_count

# ------------------------------------------------------------------------------
# FUNZIONE PER LE METRICHE (DAL NOTEBOOK)
# ------------------------------------------------------------------------------
def calculate_metrics_from_notebook(returns, total_trades, trading_days=252):
    metrics = {"Numero di Trade di Copertura": total_trades}
    cumulative_returns = (1 + returns).cumprod()
    if cumulative_returns.empty or pd.isna(cumulative_returns.iloc[-1]): return {**metrics, **{k: "N/A" for k in ["Rendimento Totale", "CAGR (ann.)", "Volatilità (ann.)", "Sharpe Ratio", "Max Drawdown", "Calmar Ratio"]}}
    total_return = cumulative_returns.iloc[-1] - 1
    num_years = len(returns) / trading_days if len(returns) > 0 else 0
    cagr = (cumulative_returns.iloc[-1]) ** (1/num_years) - 1 if num_years > 0 else 0
    volatility = returns.std() * np.sqrt(trading_days)
    sharpe_ratio = cagr / volatility if volatility > 0.0001 else 0
    cumulative_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
    metrics.update({
        "Rendimento Totale": f"{total_return:.2%}", "CAGR (ann.)": f"{cagr:.2%}", "Volatilità (ann.)": f"{volatility:.2%}",
        "Sharpe Ratio": f"{sharpe_ratio:.2f}", "Max Drawdown": f"{max_drawdown:.2%}", "Calmar Ratio": f"{calmar_ratio:.2f}"
    })
    return metrics

# ==============================================================================
# INTERFACCIA STREAMLIT
# ==============================================================================
st.set_page_config(page_title="Kriterion Quant - Backtest", page_icon="🔱", layout="wide")
st.title("🔱 Validazione Strategia Composita Scalare")

config = configparser.ConfigParser()
config.read('config.ini')
params_dict = dict(config['STRATEGY_PARAMS'])
for key, value in params_dict.items():
    try: params_dict[key] = float(value)
    except ValueError: pass

st.sidebar.header("Parametri della Strategia (da `config.ini`)")
st.sidebar.json(params_dict)

if st.button("Avvia Backtest (Logica 1:1 dal Notebook)"):
    with st.spinner("Esecuzione completa della strategia... (potrebbe richiedere alcuni minuti)"):
        equity_curves, strategy_returns, benchmark_returns, trades = run_full_strategy_from_notebook(params_dict)

        if equity_curves is not None:
            strategy_metrics = calculate_metrics_from_notebook(strategy_returns, trades)
            benchmark_metrics = calculate_metrics_from_notebook(benchmark_returns, 0)
            metrics_df = pd.DataFrame({'Strategia': strategy_metrics, 'Benchmark (SPY)': benchmark_metrics})
            
            st.subheader("Equity Line Storica")
            st.line_chart(equity_curves)
            st.subheader("Metriche di Performance")
            st.table(metrics_df)
        else:
            st.error("Esecuzione fallita. Controllare i log.")
