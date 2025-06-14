# src/indicator_calculator.py
import pandas as pd
import numpy as np
from scipy.stats import zscore

def calculate_signals(market_data, cmi_data, cmi_ma_window, vix_upper, vix_lower):
    """
    Calcola i segnali individuali e il segnale composito.
    """
    print("--- Inizio Calcolo Indicatori e Segnali ---")
    
    # Prepara il DataFrame principale solo con i dati di mercato
    data_df = pd.DataFrame({
        'SPY_Close': market_data[('Close', 'SPY')],
        'VIX_Close': market_data[('Close', '^VIX')], 
        'VIX3M_Close': market_data[('Close', '^VIX3M')]
    }).dropna()

    # --- Calcolo Segnale 1: CMI vs MA ---
    cmi_data_zscore = cmi_data.apply(zscore).dropna()
    cmi_data_zscore['Yield_Curve_10Y2Y'] *= -1
    composite_index_zscore = cmi_data_zscore.mean(axis=1)
    cmi_ma = composite_index_zscore.rolling(window=int(cmi_ma_window)).mean()
    
    # ==================== SEZIONE CORRETTA ====================
    # Crea un DataFrame CMI con le serie calcolate
    cmi_signals_df = pd.DataFrame({
        'CMI_ZScore': composite_index_zscore,
        'CMI_MA': cmi_ma
    })

    # Unisce il DataFrame di mercato con quello dei segnali CMI
    # Il join allinea le date e riempie i giorni mancanti (es. weekend)
    data_df = data_df.join(cmi_signals_df)
    
    # Propaga l'ultimo segnale CMI valido ai giorni successivi (fondamentale)
    data_df[['CMI_ZScore', 'CMI_MA']] = data_df[['CMI_ZScore', 'CMI_MA']].ffill()

    # Rimuovi le righe iniziali dove la media mobile non è ancora calcolabile
    data_df.dropna(subset=['CMI_MA'], inplace=True)
    
    data_df['Signal_CMI'] = np.where(data_df['CMI_ZScore'] > data_df['CMI_MA'], 1, 0)
    # ==========================================================
    print("Segnale CMI calcolato.")

    # --- Calcolo Segnale 2: VIX Ratio ---
    data_df['VIX_Ratio'] = data_df['VIX_Close'] / data_df['VIX3M_Close']
    signal_vix = [0] * len(data_df)
    in_hedge_signal = False
    
    # Riempiamo eventuali NaN nel VIX_Ratio prima del ciclo
    data_df['VIX_Ratio'].ffill(inplace=True)

    for i in range(len(data_df)):
        ratio = data_df['VIX_Ratio'].iloc[i]
        if ratio > vix_upper:
            in_hedge_signal = True
        elif ratio < vix_lower:
            in_hedge_signal = False
        if in_hedge_signal:
            signal_vix[i] = 1
            
    data_df['Signal_VIX'] = signal_vix
    print("Segnale VIX Ratio calcolato.")

    # --- Creazione Segnale Composito ---
    data_df['Signal_Count'] = data_df['Signal_CMI'] + data_df['Signal_VIX']
    print("Segnale Composito calcolato.")
    
    print("--- Calcolo Indicatori e Segnali Completato ---\n")
    return data_df
