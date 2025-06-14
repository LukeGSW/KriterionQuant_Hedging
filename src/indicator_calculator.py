# src/indicator_calculator.py
# Traduzione 1:1 della logica di calcolo segnali dal notebook
import pandas as pd
import numpy as np
from scipy.stats import zscore

def calculate_signals_from_notebook(market_data, cmi_data, params):
    print("--- Esecuzione Calcolo Segnali (Logica Notebook Originale) ---")

    data_df = pd.DataFrame({
        'SPY_Close': market_data['SPY_Close'], 'SPY_Open': market_data['SPY_Open'],
        'ES_Close': market_data['ES_Close'], 'ES_Open': market_data['ES_Open'],
        'VIX_Close': market_data['VIX_Close'], 'VIX3M_Close': market_data['VIX3M_Close']
    }).dropna(how='all')

    # Calcolo Segnale 1: CMI vs MA
    cmi_data_zscore = cmi_data.apply(zscore).dropna()
    cmi_data_zscore['Yield_Curve_10Y2Y'] = cmi_data_zscore['Yield_Curve_10Y2Y'] * -1
    composite_index_zscore = cmi_data_zscore.mean(axis=1)
    # NOTA: La window nel notebook è 12*21 = 252. Usiamo il parametro per coerenza.
    cmi_ma = composite_index_zscore.rolling(window=int(params['cmi_ma_window'])).mean()

    data_df['CMI_ZScore'] = composite_index_zscore
    data_df['CMI_MA'] = cmi_ma
    data_df.dropna(inplace=True) # Dropna dopo il join CMI, come da notebook

    data_df['Signal_CMI'] = np.where(data_df['CMI_ZScore'] > data_df['CMI_MA'], 1, 0)

    # Calcolo Segnale 2: VIX Ratio
    data_df['VIX_Ratio'] = data_df['VIX_Close'] / data_df['VIX3M_Close']
    signal_vix = [0] * len(data_df)
    in_hedge_signal = False
    for i in range(len(data_df)):
        ratio = data_df['VIX_Ratio'].iloc[i]
        if ratio > params['vix_ratio_upper_threshold']: in_hedge_signal = True
        elif ratio < params['vix_ratio_lower_threshold']: in_hedge_signal = False
        if in_hedge_signal: signal_vix[i] = 1
    data_df['Signal_VIX'] = signal_vix

    # Creazione Segnale Composito
    data_df['Signal_Count'] = data_df['Signal_CMI'] + data_df['Signal_VIX']
    
    return data_df
