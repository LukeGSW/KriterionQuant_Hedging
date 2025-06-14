# src/metrics_calculator.py
# Traduzione 1:1 della funzione di calcolo metriche dal notebook
import numpy as np
import pandas as pd

def calculate_metrics_from_notebook(returns, total_trades, trading_days=252):
    metrics = {"Numero di Trade di Copertura": total_trades}
    cumulative_returns = (1 + returns).cumprod()
    if cumulative_returns.empty or pd.isna(cumulative_returns.iloc[-1]):
        return {**metrics, **{k: "N/A" for k in ["Rendimento Totale", "CAGR (ann.)", "Volatilità (ann.)", "Sharpe Ratio", "Max Drawdown", "Calmar Ratio"]}}
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
