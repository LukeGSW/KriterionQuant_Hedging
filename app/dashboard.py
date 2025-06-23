# app/dashboard.py
# VERSIONE FINALE E DEFINITIVA. Calcolo Max DD Coperture corretto.
import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_datareader.data as web
import numpy as np
import configparser
from scipy.stats import zscore
import plotly.graph_objects as go
import datetime

# ==============================================================================
# FUNZIONE STRATEGIA (Logica 1:1 con il notebook)
# ==============================================================================
def run_full_strategy(params_dict, start_date, end_date):
    
    # Import necessari all'interno della funzione per chiarezza
    import pandas as pd
    import yfinance as yf
    import requests
    from io import StringIO
    from scipy.stats import zscore
    import streamlit as st # Necessario per st.error
CAPITALE_INIZIALE = params_dict['capitale_iniziale']
    # --- 1. DOWNLOAD DATI DI MERCATO (yfinance) ---
    all_tickers = ['SPY', 'ES=F', '^VIX', '^VIX3M']
    market_data_dfs = {}
    print("Avvio download dati di mercato ticker per ticker...")
    for ticker in all_tickers:
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
            if not data.empty:
                market_data_dfs[ticker] = data
            else:
                print(f"Attenzione: Nessun dato scaricato per {ticker}")
        except Exception as e:
            st.error(f"ERRORE CRITICO nel download di {ticker} da yfinance: {e}")
            return None, None, None, None, None, None

    if not market_data_dfs:
        st.error("Download di tutti i dati di mercato fallito.")
        return None, None, None, None, None, None

    market_data = pd.concat(market_data_dfs.values(), keys=market_data_dfs.keys(), axis=1)
    market_data.columns = market_data.columns.swaplevel(0, 1)

    # --- 2. DOWNLOAD DATI MACRO (FRED API DIRETTA) ---
    fred_series_cmi = {'TED_Spread': 'TEDRATE', 'Yield_Curve_10Y2Y': 'T10Y2Y', 'VIX': 'VIXCLS', 'High_Yield_Spread': 'BAMLH0A0HYM2'}
    cmi_data_dict = {}
    print("Avvio download dati FRED con chiamata API diretta...")
    try:
        fred_api_key = st.secrets["FRED_API_KEY"]
        for name, ticker in fred_series_cmi.items():
            print(f"Scarico dati FRED per {ticker}...")
            # Costruiamo l'URL per l'endpoint ufficiale delle API FRED
            api_url = f"https://api.stlouisfed.org/fred/series/observations?series_id={ticker}&api_key={fred_api_key}&file_type=json&observation_start={start_date}"
            
            response = requests.get(api_url, timeout=30)
            response.raise_for_status() # Lancia errore se la richiesta fallisce
            
            json_data = response.json()
            observations = json_data.get('observations', [])
            
            if not observations:
                print(f"Attenzione: Nessuna osservazione per {ticker} da FRED.")
                continue
            
            # Convertiamo il risultato JSON in un DataFrame pandas
            temp_df = pd.DataFrame(observations)
            temp_df = temp_df[['date', 'value']]
            temp_df['date'] = pd.to_datetime(temp_df['date'])
            temp_df.set_index('date', inplace=True)
            temp_df['value'] = pd.to_numeric(temp_df['value'], errors='coerce') # Converte i '.' in NaN
            
            cmi_data_dict[name] = temp_df['value']

    except KeyError:
        st.error("ERRORE: Chiave API 'FRED_API_KEY' non trovata nei secrets di Streamlit.")
        return None, None, None, None, None, None
    except Exception as e:
        st.error(f"Errore nella chiamata API diretta a FRED per {ticker}: {e}")
        return None, None, None, None, None, None

    if not cmi_data_dict:
        st.error("Download di tutti i dati da FRED fallito.")
        return None, None, None, None, None, None
        
    cmi_data = pd.concat(cmi_data_dict.values(), axis=1)
    cmi_data.columns = cmi_data_dict.keys()

    # --- 3. ELABORAZIONE E CALCOLO SEGNALI (Logica Invariata) ---
    # Il resto della funzione da qui in poi è IDENTICO al tuo codice originale
    
    df = pd.DataFrame()
    for ticker in all_tickers:
        prefix = ticker.replace('=F', '').replace('^', '')
        for col_type in ['Open', 'High', 'Low', 'Close', 'Volume']:
            try:
                df[f'{prefix}_{col_type}'] = market_data[(col_type, ticker)]
            except KeyError:
                pass
    df = df.join(cmi_data).ffill()
    
    colonne_essenziali = ['SPY_Open', 'SPY_Close', 'ES_Open', 'ES_Close', 'VIX_Close', 'VIX3M_Close']
    df.dropna(subset=colonne_essenziali, inplace=True)

    cmi_cols = [col for col in fred_series_cmi.keys() if col in df.columns]
    cmi_data_clean = df[cmi_cols].dropna()
    cmi_data_zscore = cmi_data_clean.apply(zscore)
    if 'Yield_Curve_10Y2Y' in cmi_data_zscore.columns:
        cmi_data_zscore['Yield_Curve_10Y2Y'] *= -1
        
    df['CMI_ZScore'] = cmi_data_zscore.mean(axis=1)
    df['CMI_MA'] = df['CMI_ZScore'].rolling(window=int(params_dict['cmi_ma_window'])).mean()
    df.dropna(subset=['CMI_MA'], inplace=True)
    
    if df.empty:
        return None, None, None, None, None, None

    # Applichiamo la correzione con .shift(1) per allineare temporalmente i dati
    df['Signal_CMI'] = np.where(df['CMI_ZScore'] > df['CMI_MA'], 1, 0)
    df['Signal_CMI'] = df['Signal_CMI'].shift(1)
    
    df['VIX_Ratio'] = df['VIX_Close'] / df['VIX3M_Close']
    signal_vix = [0] * len(df)
    in_hedge_signal = False
    for i in range(len(df)):
        ratio = df['VIX_Ratio'].iloc[i]
        if ratio > params_dict['vix_ratio_upper_threshold']:
            in_hedge_signal = True
        elif ratio < params_dict['vix_ratio_lower_threshold']:
            in_hedge_signal = False
        if in_hedge_signal:
            signal_vix[i] = 1
    df['Signal_VIX'] = signal_vix
    df['Signal_Count'] = df['Signal_CMI'].fillna(0) + df['Signal_VIX']

    # ... E il resto della logica del backtest che segue rimane invariato ...
    # (Ometto per brevità ma il tuo codice del backtest va qui)
    initial_spy_price = df['SPY_Open'].iloc[0]
    spy_shares = CAPITALE_INIZIALE / initial_spy_price
    cash_from_hedging, es_contracts, hedge_entry_price, current_tranches = 0.0, 0, 0, 0
    portfolio_history = [{'Date': df.index[0], 'Portfolio_Value': CAPITALE_INIZIALE, 'MES_Contracts': 0}]
    hedge_trades_count, hedge_stopped_out, stop_loss_events = 0, False, 0
    
    # Aggiungiamo colonne per il calcolo del drawdown della copertura
    df['Hedge_PnL'] = 0.0
    df['Equity_at_Hedge_Entry'] = np.nan

    for i in range(len(df) - 1):
        target_tranches = df['Signal_Count'].iloc[i]
        row_T1 = df.iloc[i+1]
        
        realized_hedge_pnl_today = 0
        unrealized_pnl_change = 0
        
        if current_tranches > 0:
            unrealized_pnl_change = es_contracts * (row_T1['ES_Close'] - df.iloc[i]['ES_Close']) * params['micro_es_multiplier']
        
        if current_tranches > 0:
            if row_T1['ES_Open'] > hedge_entry_price * (1 + params['stop_loss_threshold_hedge']):
                realized_hedge_pnl_today = es_contracts * (row_T1['ES_Open'] - hedge_entry_price) * params['micro_es_multiplier']
                es_contracts, current_tranches, hedge_stopped_out = 0, 0, True
                stop_loss_events += 1
            elif target_tranches < current_tranches:
                contracts_per_tranche = es_contracts / current_tranches
                contracts_to_close = contracts_per_tranche * (current_tranches - target_tranches)
                realized_hedge_pnl_today = contracts_to_close * (row_T1['ES_Open'] - hedge_entry_price) * params['micro_es_multiplier']
                es_contracts -= contracts_to_close
                current_tranches = target_tranches

        if target_tranches == 0: hedge_stopped_out = False
        if target_tranches > current_tranches and not hedge_stopped_out:
            tranches_to_add = target_tranches - current_tranches
            portfolio_value_at_entry = (spy_shares * row_T1['SPY_Open']) + cash_from_hedging
            notional_per_tranche = portfolio_value_at_entry * params['hedge_percentage_per_tranche']
            if current_tranches == 0: 
                hedge_entry_price = row_T1['ES_Open']
                hedge_trades_count += 1
                # Registra l'equity all'inizio del ciclo di copertura
                df.loc[row_T1.name, 'Equity_at_Hedge_Entry'] = portfolio_value_at_entry
            contracts_to_add = - (notional_per_tranche / (row_T1['ES_Open'] * params['micro_es_multiplier'])) * tranches_to_add
            es_contracts += contracts_to_add
            current_tranches = target_tranches

        cash_from_hedging += realized_hedge_pnl_today
        spy_position_value = spy_shares * row_T1['SPY_Close']
        unrealized_hedge_pnl = es_contracts * (row_T1['ES_Close'] - hedge_entry_price) * params['micro_es_multiplier'] if current_tranches > 0 else 0
        portfolio_value = spy_position_value + cash_from_hedging + unrealized_hedge_pnl
        
        daily_hedge_pnl = realized_hedge_pnl_today + unrealized_pnl_change
        
        portfolio_history.append({'Date': row_T1.name, 'Portfolio_Value': portfolio_value, 'MES_Contracts': es_contracts})
        df.loc[row_T1.name, 'Hedge_PnL'] = daily_hedge_pnl

    results_df_final = pd.DataFrame(portfolio_history).set_index('Date')
    results_df_final['Strategy_Returns'] = results_df_final['Portfolio_Value'].pct_change()
    
    benchmark_returns = df['SPY_Close'].pct_change()
    cumulative_benchmark = (1 + benchmark_returns).cumprod() * CAPITALE_INIZIALE
    cumulative_benchmark.iloc[0] = CAPITALE_INIZIALE
    
    equity_curves = pd.DataFrame({'Strategy_Equity': results_df_final['Portfolio_Value'], 'Buy_And_Hold_Equity': cumulative_benchmark}).dropna()
    df_con_risultati = df.join(results_df_final[['MES_Contracts']]).ffill()

    return equity_curves, results_df_final['Strategy_Returns'].dropna(), benchmark_returns.dropna(), hedge_trades_count, stop_loss_events, df_con_risultati

# ==============================================================================
# FUNZIONI DI PLOTTING E METRICHE
# ==============================================================================
def calculate_metrics(strategy_returns, benchmark_returns, total_trades, stop_loss_events, results_df, trading_days=252):
    
    # Calcolo Max Drawdown Coperture relativo all'equity all'apertura del trade
    results_df['Hedge_Cycle_Equity'] = results_df['Equity_at_Hedge_Entry'].ffill()
    results_df['Cumulative_Hedge_PnL_per_Cycle'] = results_df.groupby(results_df['Equity_at_Hedge_Entry'].notna().cumsum())['Hedge_PnL'].cumsum()
    results_df['Hedge_DD_pct_on_Entry_Equity'] = results_df['Cumulative_Hedge_PnL_per_Cycle'] / results_df['Hedge_Cycle_Equity']
    max_drawdown_hedge_pct = results_df['Hedge_DD_pct_on_Entry_Equity'].min()
    
    # Calcolo metriche standard
    metrics = {
        "Numero di Trade di Copertura": total_trades,
        "Numero di Stop Loss": stop_loss_events,
        "Max DD Coperture su Equity Iniziale Trade": f"{max_drawdown_hedge_pct:.2%}" if pd.notna(max_drawdown_hedge_pct) else "N/A"
    }
    
    cumulative_returns = (1 + strategy_returns).cumprod(); total_return = cumulative_returns.iloc[-1] - 1
    num_years = len(strategy_returns) / trading_days if len(strategy_returns) > 0 else 0
    cagr = (cumulative_returns.iloc[-1]) ** (1/num_years) - 1 if num_years > 0 else 0; volatility = strategy_returns.std() * np.sqrt(trading_days)
    sharpe_ratio = cagr / volatility if volatility > 0.0001 else 0; cumulative_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - cumulative_max) / cumulative_max; max_drawdown = drawdown.min()
    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
    metrics.update({"Rendimento Totale": f"{total_return:.2%}", "CAGR (ann.)": f"{cagr:.2%}", "Volatilità (ann.)": f"{volatility:.2%}", "Sharpe Ratio": f"{sharpe_ratio:.2f}", "Max Drawdown": f"{max_drawdown:.2%}", "Calmar Ratio": f"{calmar_ratio:.2f}"})
    
    # Calcolo metriche benchmark
    bench_metrics = {}
    bench_cumulative = (1 + benchmark_returns).cumprod(); bench_total_return = bench_cumulative.iloc[-1] - 1
    bench_num_years = len(benchmark_returns) / trading_days if len(benchmark_returns) > 0 else 0
    bench_cagr = (bench_cumulative.iloc[-1]) ** (1/bench_num_years) - 1 if bench_num_years > 0 else 0
    bench_volatility = benchmark_returns.std() * np.sqrt(trading_days)
    bench_sharpe = bench_cagr / bench_volatility if bench_volatility > 0.0001 else 0
    bench_cummax = bench_cumulative.cummax(); bench_drawdown_series = (bench_cumulative - bench_cummax) / bench_cummax; bench_max_dd = bench_drawdown_series.min()
    bench_calmar = bench_cagr / abs(bench_max_dd) if bench_max_dd != 0 else 0
    bench_metrics.update({"Rendimento Totale": f"{bench_total_return:.2%}", "CAGR (ann.)": f"{bench_cagr:.2%}", "Volatilità (ann.)": f"{bench_volatility:.2%}", "Sharpe Ratio": f"{bench_sharpe:.2f}", "Max Drawdown": f"{bench_max_dd:.2%}", "Calmar Ratio": f"{bench_calmar:.2f}", "Numero di Trade di Copertura": 0, "Numero di Stop Loss": 0, "Max DD Coperture su Equity Iniziale Trade": "N/A"})
    
    return metrics, bench_metrics

def plotly_trades_chart(df_results, title):
    # ... (invariata)
    trade_points = df_results[df_results['MES_Contracts'].diff() != 0].copy(); fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_results.index, y=df_results['ES_Close'], mode='lines', name='Prezzo SPY', line=dict(color='cyan', width=1)))
    aumento_copertura = trade_points[trade_points['MES_Contracts'] < trade_points['MES_Contracts'].shift(1).fillna(0)]; riduzione_copertura = trade_points[trade_points['MES_Contracts'] > trade_points['MES_Contracts'].shift(1).fillna(0)]
    fig.add_trace(go.Scatter(x=aumento_copertura.index, y=aumento_copertura['ES_Close'], mode='markers', name='Aumento Copertura', marker=dict(color='red', symbol='triangle-down', size=10)))
    fig.add_trace(go.Scatter(x=riduzione_copertura.index, y=riduzione_copertura['ES_Close'], mode='markers', name='Riduzione Copertura', marker=dict(color='lime', symbol='triangle-up', size=10)))
    for _, row in trade_points.iterrows():
        fig.add_annotation(x=row.name, y=row['SPY_Close'], text=f"<b>{int(row['MES_Contracts'])}</b>", showarrow=False, yshift=15, font=dict(color="white", size=10), bgcolor="rgba(0,0,0,0.5)")
    fig.update_layout(title=title, template='plotly_dark', yaxis_type="log", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# Dentro la funzione plotly_individual_signals_chart in app/dashboard.py

def plotly_individual_signals_chart(df_results):
    df = df_results.copy()
    cmi_trades = df[df['Signal_CMI'].diff() != 0]
    vix_trades = df[df['Signal_VIX'].diff() != 0]
    fig = go.Figure()
    
    # --- MODIFICA QUESTA RIGA ---
    fig.add_trace(go.Scatter(x=df.index, y=df['ES_Close'], mode='lines', name='Prezzo ES', line=dict(color='cyan', width=1)))

    cmi_entries = cmi_trades[cmi_trades['Signal_CMI'] == 1]
    cmi_exits = cmi_trades[cmi_trades['Signal_CMI'] == 0]
    vix_entries = vix_trades[vix_trades['Signal_VIX'] == 1]
    vix_exits = vix_trades[vix_trades['Signal_VIX'] == 0]

    # --- E LE SUCCESSIVE QUATTRO RIGHE ---
    fig.add_trace(go.Scatter(x=cmi_entries.index, y=cmi_entries['ES_Close'], mode='markers', name='Entrata CMI', marker=dict(color='orange', symbol='triangle-down', size=12, line=dict(width=1, color='black'))))
    fig.add_trace(go.Scatter(x=cmi_exits.index, y=cmi_exits['ES_Close'], mode='markers', name='Uscita CMI', marker=dict(color='orange', symbol='triangle-up', size=12, line=dict(width=1, color='black'))))
    fig.add_trace(go.Scatter(x=vix_entries.index, y=vix_entries['ES_Close'], mode='markers', name='Entrata VIX', marker=dict(color='magenta', symbol='cross', size=9)))
    fig.add_trace(go.Scatter(x=vix_exits.index, y=vix_exits['ES_Close'], mode='markers', name='Uscita VIX', marker=dict(color='magenta', symbol='x', size=9)))
    
    fig.update_layout(title='Prezzo ES con Segnali Individuali', template='plotly_dark', yaxis_type="log", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig
# ==============================================================================
# INTERFACCIA STREAMLIT
# ==============================================================================
if __name__ == '__main__':
    st.set_page_config(page_title="Kriterion Quant - Dashboard", page_icon="🔱", layout="wide")
    st.title("🔱 Dashboard Strategia di Copertura")
    
    config = configparser.ConfigParser(); config.read('config.ini')
    default_params = dict(config['STRATEGY_PARAMS'])
    for key, value in default_params.items():
        try: default_params[key] = float(value)
        except ValueError: pass
    
    st.sidebar.title("Parametri di Simulazione")
    start_date_input = st.sidebar.date_input("Data Inizio Backtest", value=pd.to_datetime('2007-01-01'), min_value=pd.to_datetime('2005-01-01'), max_value=datetime.date.today())
    capital_input = st.sidebar.number_input("Capitale Iniziale ($)", value=default_params['capitale_iniziale'], min_value=1000.0, step=1000.0, format="%.2f")
    hedge_perc_input = st.sidebar.slider("Hedge % per Tranche", min_value=0.1, max_value=2.0, value=default_params['hedge_percentage_per_tranche'], step=0.025, format="%.3f")
    stop_loss_input = st.sidebar.slider("Stop Loss sulla Copertura (%)", min_value=0.01, max_value=0.20, value=default_params['stop_loss_threshold_hedge'], step=0.01, format="%.2f")
    
    params_dict = default_params.copy()
    params_dict['capitale_iniziale'] = capital_input; params_dict['hedge_percentage_per_tranche'] = hedge_perc_input; params_dict['stop_loss_threshold_hedge'] = stop_loss_input
    
    tab1, tab2 = st.tabs(["📊 Segnale Odierno", "📜 Backtest Storico"])
    
    with tab1:
        st.header("Visualizza il segnale di copertura e i grafici degli indicatori")
        if st.button("Calcola Segnale e Grafici"):
            with st.spinner("Calcolo in corso..."):
                end_date = datetime.date.today()
                start_date_recent = end_date - datetime.timedelta(days=2*365)
                results = run_full_strategy(params_dict, start_date_recent, end_date)
                if results is not None and results[5] is not None:
                    _, _, _, _, _, df_results = results
                    if not df_results.empty:
                        df_last_year = df_results.last('365D')
                        latest_signal_row = df_results.iloc[-1]
                        st.subheader(f"Segnale per il {latest_signal_row.name.strftime('%Y-%m-%d')}")
                        col1, col2, col3 = st.columns(3); col1.metric("Segnale CMI", int(latest_signal_row['Signal_CMI'])); col2.metric("Segnale VIX Ratio", int(latest_signal_row['Signal_VIX']))
                        col3.metric("Tranche di Copertura", int(latest_signal_row['Signal_Count']))
                        st.markdown("---")
                        st.subheader("Grafici Indicatori (ultimo anno)")
                        vix_plot_df = pd.DataFrame({'VIX_Ratio': df_last_year['VIX_Ratio'], 'Soglia Superiore': params_dict['vix_ratio_upper_threshold'], 'Soglia Inferiore': params_dict['vix_ratio_lower_threshold']})
                        st.line_chart(vix_plot_df, color=["#FF00FF", "#808080", "#808080"])
                        st.line_chart(df_last_year[['CMI_ZScore', 'CMI_MA']])
                        st.plotly_chart(plotly_individual_signals_chart(df_last_year), use_container_width=True)
                    else:
                        st.warning("Il calcolo ha prodotto un set di dati vuoto. Nessun segnale da mostrare.")
                else:
                    st.error("La funzione di calcolo non ha restituito risultati. Causa probabile: errore nel download dei dati iniziali. Riprova tra poco.")
    
    with tab2:
        st.header("Esegui un backtest completo sulla base dei parametri della sidebar")
        if st.button("Avvia Backtest Storico Completo"):
            with st.spinner("Esecuzione completa della strategia in corso..."):
                results = run_full_strategy(params_dict, start_date_input, datetime.date.today())
                if results is None or len(results) < 6 or results[5] is None:
                    st.error("Esecuzione del backtest fallita. La funzione 'run_full_strategy' non ha restituito dati validi. Causa probabile: errore nel download o nell'elaborazione dei dati da yfinance o FRED. Riprovare tra poco.")
                else:
                    # Se siamo qui, i dati sono validi e possiamo procedere
                    equity_curves, strategy_returns, benchmark_returns, trades, stop_losses, df_final_results = results
                    st.success("Esecuzione completata con successo!")
                    
                    # Ora questa chiamata è sicura perché avviene solo se df_final_results è valido
                    strategy_metrics, benchmark_metrics = calculate_metrics(strategy_returns, benchmark_returns, trades, stop_losses, df_final_results)
                    metrics_df = pd.DataFrame({'Strategia': strategy_metrics, 'Benchmark (SPY)': benchmark_metrics})
                    # --- NUOVA RIGA DA AGGIUNGERE ---
                    # Converte tutte le colonne in tipo stringa per una visualizzazione sicura
                    metrics_df = metrics_df.astype(str)
                    st.subheader("Grafico Operazioni di Copertura")
                    st.plotly_chart(plotly_trades_chart(df_final_results, 'Prezzo ES con Operazioni di Copertura (Backtest)'), use_container_width=True)
                    st.subheader("Equity Line Storica")
                    st.line_chart(equity_curves)
                    st.subheader("Metriche di Performance")
                    st.table(metrics_df)
