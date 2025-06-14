# src/indicator_calculator.py
# Utilizza la struttura MultiIndex originale di yfinance, come nel notebook
import pandas as pd
import numpy as np
from scipy.stats import zscore

def calculate_signals_from_notebook(market_data, cmi_data, params):
    print("--- Esecuzione Calcolo Segnali (Logica Notebook Originale) ---")

    # Legge i dati usando la sintassi a Tuple (MultiIndex), identica al notebook
    data_df = pd.DataFrame({
        'SPY_Close': market_data[('Close', 'SPY')], 'SPY_Open': market_data[('Open', 'SPY')],
        'ES_Close': market_data[('Close', 'ES=F')], 'ES_Open': market_data[('Open', 'ES=F')],
        'VIX_Close': market_data[('Close', '^VIX')], 'VIX3M_Close': market_data[('Close', '^VIX3M')]
    }).dropna(how='all')

    # Il resto della logica è identico a prima e al notebook
    cmi_data_zscore = cmi_data.apply(zscore).dropna()
    cmi_data_zscore['Yield_Curve_10Y2Y'] = cmi_data_zscore['Yield_Curve_10Y2Y'] * -1
    composite_index_zscore = cmi_data_zscore.mean(axis=1)
    cmi_ma = composite_index_zscore.rolling(window=int(params['cmi_ma_window'])).mean()

    data_df['CMI_ZScore'] = composite_index_zscore
    data_df['CMI_MA'] = cmi_ma
    data_df.dropna(inplace=True)

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
    
    return data_df
