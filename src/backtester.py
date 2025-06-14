# src/backtester.py
# VERSIONE FINALE E COMPLETA, CON STOP LOSS INTEGRATO
import numpy as np
import pandas as pd

def run_historical_backtest(df_signals, params):
    """
    Esegue il backtest storico completo, inclusa la logica di stop loss,
    e calcola le metriche di performance.
    """
    print("--- Avvio Backtest Storico con Logica Stop Loss Attiva ---")
    
    # Inizializzazione parametri
    capitale_iniziale = params['capitale_iniziale']
    hedge_percentage_per_tranche = params['hedge_percentage_per_tranche']
    stop_loss_threshold_hedge = params['stop_loss_threshold_hedge']
    micro_es_multiplier = params['micro_es_multiplier']
    
    # 1. Calcolo del portafoglio base (Buy and Hold)
    df_signals['Buy_And_Hold_Equity'] = capitale_iniziale * (1 + df_signals['SPY_Close'].pct_change()).cumprod().fillna(capitale_iniziale)

    # 2. Inizializzazione colonne per il backtest con Stop Loss
    df_signals['Hedge_PnL'] = 0.0
    df_signals['MES_Contracts'] = 0
    df_signals['Stop_Loss_Triggered'] = 0
    df_signals['Strategy_Equity'] = df_signals['Buy_And_Hold_Equity'] # Inizia uguale al B&H

    # Variabili per la gestione dello stato dello SL
    stop_loss_active = False
    stop_loss_level = 0
    
    # Ciclo di backtesting
    for i in range(1, len(df_signals)):
        prev_row = df_signals.iloc[i-1]
        current_row = df_signals.iloc[i]
        
        # Valore dell'equity della strategia alla chiusura di ieri
        equity_yesterday = df_signals.loc[prev_row.name, 'Strategy_Equity']

        # A. Controlla se lo Stop Loss è stato attivato ieri sera
        if stop_loss_active and equity_yesterday <= stop_loss_level:
            # Stop Loss colpito! La posizione di copertura viene chiusa all'apertura di oggi.
            # Non si accumula P&L sulla copertura per oggi.
            MES_contracts_in_position = 0
            stop_loss_active = False
            df_signals.loc[current_row.name, 'Stop_Loss_Triggered'] = 1
        else:
            # Nessuno stop, la posizione di ieri rimane valida per il calcolo del P&L di oggi
            MES_contracts_in_position = prev_row['MES_Contracts']
            
        # B. Calcola il P&L del giorno sulla posizione di copertura tenuta da ieri
        price_change = current_row['SPY_Close'] - prev_row['SPY_Close']
        daily_pnl = MES_contracts_in_position * micro_es_multiplier * price_change
        df_signals.loc[current_row.name, 'Hedge_PnL'] = daily_pnl

        # C. Calcola l'equity della strategia *prima* di eventuali nuovi trade
        df_signals.loc[current_row.name, 'Strategy_Equity'] = equity_yesterday + (current_row['Buy_And_Hold_Equity'] - prev_row['Buy_And_Hold_Equity']) + daily_pnl

        # D. Determina la nuova posizione di copertura per domani, basata sul segnale di oggi
        signal_today = current_row['Signal_Count']
        target_hedge_value = capitale_iniziale * hedge_percentage_per_tranche * signal_today
        
        if current_row['SPY_Close'] > 0:
            new_contracts_target = -round(target_hedge_value / (micro_es_multiplier * current_row['SPY_Close']))
        else:
            new_contracts_target = 0
        df_signals.loc[current_row.name, 'MES_Contracts'] = new_contracts_target
        
        # E. Imposta un nuovo livello di Stop Loss se apriamo una posizione di copertura
        if new_contracts_target != 0 and MES_contracts_in_position == 0:
            # Si apre una nuova posizione di copertura
            stop_loss_level = df_signals.loc[current_row.name, 'Strategy_Equity'] * (1 - stop_loss_threshold_hedge)
            stop_loss_active = True
        elif new_contracts_target == 0:
            # La copertura è chiusa, disattiva lo SL
            stop_loss_active = False

    # 4. Calcolo Metriche di Performance (sull'equity finale e completa)
    strategy_returns = df_signals['Strategy_Equity'].pct_change().dropna()
    cagr = (df_signals['Strategy_Equity'].iloc[-1] / capitale_iniziale) ** (252 / len(df_signals)) - 1
    annual_volatility = strategy_returns.std() * np.sqrt(252)
    sharpe_ratio = cagr / annual_volatility if annual_volatility != 0 else 0
    
    downside_returns = strategy_returns[strategy_returns < 0]
    sortino_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 1 else 0
    sortino_ratio = cagr / sortino_volatility if sortino_volatility != 0 else 0
    
    cumulative_max = df_signals['Strategy_Equity'].cummax()
    drawdown = (df_signals['Strategy_Equity'] - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0

    metrics = {
        "CAGR": f"{cagr:.2%}",
        "Annual Volatility": f"{annual_volatility:.2%}",
        "Sharpe Ratio": f"{sharpe_ratio:.2f}",
        "Sortino Ratio": f"{sortino_ratio:.2f}",
        "Max Drawdown": f"{max_drawdown:.2%}",
        "Calmar Ratio": f"{calmar_ratio:.2f}",
        "Numero di Stop Loss": int(df_signals['Stop_Loss_Triggered'].sum())
    }

    equity_curves = df_signals[['Strategy_Equity', 'Buy_And_Hold_Equity']]
    
    print("--- Backtest Storico Corretto con Stop Loss Completato ---")
    return equity_curves, metrics
