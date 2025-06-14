# src/indicator_calculator.py
# VERSIONE FINALE ALLINEATA ALLA LOGICA DEL NOTEBOOK ORIGINALE
import pandas as pd
import numpy as np
from scipy.stats import zscore

def calculate_signals(market_data, cmi_data, cmi_ma_window, vix_upper, vix_lower):
    """
    Calcola i segnali di copertura replicando fedelmente la logica del notebook Kriterion.
    Le uniche modifiche riguardano la gestione robusta dei dati per l'ambiente di produzione.
    """
    print("--- Inizio Calcolo Indicatori - Aderenza alla logica originale ---")
    
    # 1. Preparazione DataFrame principale con dati di mercato
    data_df = pd.DataFrame({
        'SPY_Close': market_data[('Close', 'SPY')],
        'VIX_Close': market_data[('Close', '^VIX')], 
        'VIX3M_Close': market_data[('Close', '^VIX3M')]
    }).dropna(how='all')

    # 2. Calcolo CMI - Logica 1:1 con il notebook
    if cmi_data.empty:
        # Caso di emergenza se i dati FRED non sono disponibili
        data_df['Signal_CMI'] = 0
    else:
        cmi_data_zscore = cmi_data.apply(zscore).dropna()
        cmi_data_zscore['Yield_Curve_10Y2Y'] *= -1
        composite_index_zscore = cmi_data_zscore.mean(axis=1)
        cmi_ma = composite_index_zscore.rolling(window=int(cmi_ma_window)).mean()
        
        cmi_signals_df = pd.DataFrame({
            'CMI_ZScore': composite_index_zscore,
            'CMI_MA': cmi_ma
        })

        # Unione robusta dei dati CMI con i dati di mercato
        data_df = data_df.join(cmi_signals_df)
        # Propagazione forward per gestire i giorni non lavorativi dei dati macro
        data_df[['CMI_ZScore', 'CMI_MA']] = data_df[['CMI_ZScore', 'CMI_MA']].ffill()
        
        # Calcolo segnale CMI - Logica 1:1 con il notebook
        data_df['Signal_CMI'] = np.where(data_df['CMI_ZScore'] > data_df['CMI_MA'], 1, 0)
    
    print("Segnale CMI calcolato.")

    # 3. Calcolo VIX Ratio - Logica 1:1 con il notebook
    data_df['VIX_Ratio'] = data_df['VIX_Close'] / data_df['VIX3M_Close']
    signal_vix = [0] * len(data_df)
    in_hedge_signal = False
    
    # Propagazione forward per gestire eventuali dati mancanti
    data_df['VIX_Ratio'] = data_df['VIX_Ratio'].ffill()

    # Ciclo di isteresi - Logica 1:1 con il notebook
    for i in range(len(data_df)):
        ratio = data_df['VIX_Ratio'].iloc[i]
        if not pd.isna(ratio):
            if ratio > vix_upper:
                in_hedge_signal = True
            elif ratio < vix_lower:
                in_hedge_signal = False
            
            if in_hedge_signal:
                signal_vix[i] = 1
            
    data_df['Signal_VIX'] = signal_vix
    print("Segnale VIX Ratio calcolato.")

    # 4. Creazione Segnale Composito - Logica 1:1 con il notebook
    data_df['Signal_Count'] = data_df['Signal_CMI'] + data_df['Signal_VIX']
    print("Segnale Composito calcolato.")
    
    # 5. Pulizia finale - Simula il dropna() del notebook ma in modo sicuro
    # Eliminiamo solo le righe dove i calcoli iniziali non erano possibili
    final_df = data_df.dropna(subset=['SPY_Close', 'CMI_MA', 'VIX_Ratio'])
    
    print("--- Calcolo Indicatori e Segnali Completato ---\n")
    return final_df
