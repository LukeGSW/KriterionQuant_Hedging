# src/backtester.py
# Traduzione 1:1 della logica di backtest (STEP 5) dal notebook
import pandas as pd

def run_backtest_from_notebook(data_df, params):
    print("--- Esecuzione Backtest (Logica Notebook Originale) ---")
    
    CAPITALE_INIZIALE = params['capitale_iniziale']
    HEDGE_PERCENTAGE_PER_TRANCHE = params['hedge_percentage_per_tranche']
    STOP_LOSS_THRESHOLD_HEDGE = params['stop_loss_threshold_hedge']
    MICRO_ES_MULTIPLIER = params['micro_es_multiplier']

    initial_spy_price = data_df['SPY_Open'].iloc[0]
    spy_shares = CAPITALE_INIZIALE / initial_spy_price
    cash_from_hedging = 0.0
    es_contracts, hedge_entry_price, current_tranches = 0, 0, 0
    portfolio_history = [{'Date': data_df.index[0], 'Portfolio_Value': CAPITALE_INIZIALE}]
    hedge_trades_count = 0
    in_hedge, hedge_stopped_out = False, False

    for i in range(len(data_df) - 1):
        target_tranches = data_df['Signal_Count'].iloc[i]
        date_T1, open_spy_T1, open_es_T1, close_spy_T1, close_es_T1 = \
            data_df.index[i+1], data_df['SPY_Open'].iloc[i+1], data_df['ES_Open'].iloc[i+1], \
            data_df['SPY_Close'].iloc[i+1], data_df['ES_Close'].iloc[i+1]
        
        realized_hedge_pnl_today = 0
        
        if current_tranches > 0:
            if open_es_T1 > hedge_entry_price * (1 + STOP_LOSS_THRESHOLD_HEDGE):
                realized_hedge_pnl_today = es_contracts * (open_es_T1 - hedge_entry_price) * MICRO_ES_MULTIPLIER
                es_contracts, current_tranches, hedge_stopped_out = 0, 0, True
            elif target_tranches < current_tranches:
                contracts_per_tranche = es_contracts / current_tranches
                contracts_to_close = contracts_per_tranche * (current_tranches - target_tranches)
                realized_hedge_pnl_today = contracts_to_close * (open_es_T1 - hedge_entry_price) * MICRO_ES_MULTIPLIER
                es_contracts -= contracts_to_close
                current_tranches = target_tranches

        if target_tranches == 0: hedge_stopped_out = False
            
        if target_tranches > current_tranches and not hedge_stopped_out:
            tranches_to_add = target_tranches - current_tranches
            portfolio_value_at_entry = (spy_shares * open_spy_T1) + cash_from_hedging
            notional_per_tranche = portfolio_value_at_entry * HEDGE_PERCENTAGE_PER_TRANCHE
            if current_tranches == 0:
                hedge_entry_price = open_es_T1
                hedge_trades_count += 1
            contracts_to_add = - (notional_per_tranche / (open_es_T1 * MICRO_ES_MULTIPLIER)) * tranches_to_add
            es_contracts += contracts_to_add
            current_tranches = target_tranches

        cash_from_hedging += realized_hedge_pnl_today
        spy_position_value = spy_shares * close_spy_T1
        unrealized_hedge_pnl = es_contracts * (close_es_T1 - hedge_entry_price) * MICRO_ES_MULTIPLIER if current_tranches > 0 else 0
        portfolio_value = spy_position_value + cash_from_hedging + unrealized_hedge_pnl
        portfolio_history.append({'Date': date_T1, 'Portfolio_Value': portfolio_value})
        
    results_df_final = pd.DataFrame(portfolio_history).set_index('Date')
    results_df_final['Strategy_Returns'] = results_df_final['Portfolio_Value'].pct_change()
    
    # Calcolo benchmark B&H
    benchmark_returns = data_df['SPY_Close'].pct_change()
    cumulative_benchmark = (1 + benchmark_returns).cumprod() * CAPITALE_INIZIALE
    cumulative_benchmark.iloc[0] = CAPITALE_INIZIALE
    
    equity_curves = pd.DataFrame({
        'Strategy_Equity': results_df_final['Portfolio_Value'],
        'Buy_And_Hold_Equity': cumulative_benchmark
    }).dropna()

    return equity_curves, results_df_final['Strategy_Returns'].dropna(), benchmark_returns.dropna(), hedge_trades_count
