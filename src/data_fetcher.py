# src/data_fetcher.py
# CORREZIONE FINALE per accettare l'oggetto config
import pandas as pd
import yfinance as yf
import pandas_datareader.data as web
import datetime as dt
import ast

# La funzione ora accetta l'intero oggetto 'config'
def fetch_all_data(config, market_tickers, start_date_str=None):
    print("--- Inizio Download Dati ---")
    
    # Estrae la stringa dal config e la converte, come dovrebbe essere
    fred_series_str = config.get('DATA', 'fred_series_cmi')
    fred_series_cmi = ast.literal_eval(fred_series_str)
    
    if start_date_str is None:
        end_date = pd.to_datetime('today').normalize()
        start_date = end_date - pd.DateOffset(years=3)
    else:
        start_date = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime('today').normalize()

    # Download Dati di Mercato (logica precedente invariata)
    try:
        # Abbiamo rimosso il download 1-a-1 per tornare alla logica originale
        # e per evitare problemi con la struttura delle colonne
        market_data = yf.download(market_tickers, start=start_date, end=end_date, progress=False, auto_adjust=False)
        # Rinomina le colonne per rimuovere i tuple (es. ('Close', 'SPY') -> 'Close_SPY')
        market_data.columns = [f'{col[0]}_{col[1].replace("=", "")}' for col in market_data.columns]
        market_data.rename(columns=lambda x: x.replace('^', ''), inplace=True)

        if market_data.empty:
            print("ATTENZIONE: yfinance ha restituito un DataFrame vuoto.")
        else:
            print("Dati di Mercato da Yahoo Finance scaricati.")
    except Exception as e:
        print(f"Errore critico nel download dei dati di mercato: {e}")
        market_data = pd.DataFrame()

    # Download Dati Macro (logica precedente invariata)
    try:
        cmi_data_dict = {}
        for name, ticker in fred_series_cmi.items():
            cmi_data_dict[name] = web.DataReader(ticker, 'fred', start_date, end_date)
        cmi_data = pd.concat(cmi_data_dict.values(), axis=1)
        cmi_data.columns = fred_series_cmi.keys()
        cmi_data.ffill(inplace=True)
        print("Dati Macro (CMI) da FRED scaricati.")
    except Exception as e:
        print(f"Errore critico nel download dei dati CMI: {e}")
        cmi_data = pd.DataFrame()
            
    print("--- Download Dati Completato ---\n")
    return market_data, cmi_data
