# src/backtester.py
# Contiene la logica di backtesting storico estratta 1:1 dal notebook originale.
import numpy as np
import pandas as pd

def run_historical_backtest(df_signals, params):
    """
    Esegue il backtest storico completo e calcola le metriche di performance.
    La logica è una replica fedele dello script finale del notebook.
    """
    print("--- Avvio Backtest Storico ---")
    
    # Inizializzazione parametri dal dizionario
    capitale_iniziale = params['capitale_iniziale']
    hedge_percentage_per_tranche = params['hedge_percentage_per_tranche']
    stop_loss_threshold_hedge = params['stop_loss_threshold_hedge']
    micro_es_multiplier = params['micro_es_multiplier']
    
    # Preparazione colonne per il backtest
    df_signals['ES_Returns'] = df_signals['SPY_Close'].pct_change() # Usiamo SPY come proxy per i rendimenti di ES
    df_signals['Buy_And_Hold_Equity'] = capitale_iniziale * (1 + df_signals['ES_Returns']).cumprod()
    df_signals['Strategy_Equity'] = capitale_iniziale
    df_signals['MES_Contracts'] = 0
    df_signals['Stop_Loss_Triggered'] = 0

    cash = capitale_iniziale
    MES_contracts_in_position = 0
    stop_loss_level = 0
    stop_loss_active = False

    # Ciclo di backtesting - Logica 1:1 con il notebook
    for i in range(1, len(df_signals)):
        prev_row = df_signals.iloc[i-1]
        current_row = df_signals.iloc[i]

        # Calcolo del valore del portafoglio all'inizio del giorno
        portfolio_value = cash + (MES_contracts_in_position * micro_es_multiplier * current_row['SPY_Close'])

        # Gestione Stop Loss
        if stop_loss_active and portfolio_value <= stop_loss_level:
            cash += MES_contracts_in_position * micro_es_multiplier * current_row['SPY_Close']
            MES_contracts_in_position = 0
            stop_loss_active = False
            df_signals.loc[df_signals.index[i], 'Stop_Loss_Triggered'] = 1

        # Logica di trading basata sul segnale del giorno prima (T+1)
        signal = prev_row['Signal_Count']
        target_hedge_value = capitale_iniziale * hedge_percentage_per_tranche * signal
        target_MES_contracts = -round(target_hedge_value / (micro_es_multiplier * prev_row['SPY_Close']))

        if target_MES_contracts != MES_contracts_in_position:
            contracts_to_trade = target_MES_contracts - MES_contracts_in_position
            trade_cost = contracts_to_trade * micro_es_multiplier * current_row['SPY_Close']
            cash -= trade_cost
            MES_contracts_in_position += contracts_to_trade

            if target_MES_contracts != 0:
                stop_loss_level = portfolio_value * (1 - stop_loss_threshold_hedge)
                stop_loss_active = True
            else:
                stop_loss_active = False

        # Aggiornamento valori
        df_signals.loc[df_signals.index[i], 'MES_Contracts'] = MES_contracts_in_position
        final_portfolio_value = cash + (MES_contracts_in_position * micro_es_multiplier * current_row['SPY_Close'])
        df_signals.loc[df_signals.index[i], 'Strategy_Equity'] = final_portfolio_value

    # Calcolo Metriche di Performance - Logica 1:1 con il notebook
    strategy_returns = df_signals['Strategy_Equity'].pct_change().dropna()
    cagr = (df_signals['Strategy_Equity'].iloc[-1] / capitale_iniziale) ** (252 / len(df_signals)) - 1
    annual_volatility = strategy_returns.std() * np.sqrt(252)
    sharpe_ratio = cagr / annual_volatility if annual_volatility != 0 else 0
    
    downside_returns = strategy_returns[strategy_returns < 0]
    sortino_volatility = downside_returns.std() * np.sqrt(252)
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
    
    print("--- Backtest Storico Completato ---")
    return equity_curves, metrics
