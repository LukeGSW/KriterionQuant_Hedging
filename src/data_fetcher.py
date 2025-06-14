# src/data_fetcher.py (Versione CORRETTA)
import pandas as pd
import yfinance as yf
import pandas_datareader.data as web
import datetime as dt
import ast

def fetch_all_data(fred_series_str, market_tickers):
    """
    Scarica tutti i dati necessari, sia da FRED che da Yahoo Finance.
    """
    print("--- Inizio Download Dati ---")
    
    fred_series_cmi = ast.literal_eval(fred_series_str)

    end_date = pd.to_datetime('today').normalize()
    start_date_mkt = end_date - pd.DateOffset(years=2)
    start_date_cmi = end_date - pd.DateOffset(years=3)
    
    # 1. Download Dati Macro (CMI) da FRED
    try:
        cmi_data_dict = {}
        for name, ticker in fred_series_cmi.items():
            cmi_data_dict[name] = web.DataReader(ticker, 'fred', start_date_cmi, end_date)
        cmi_data = pd.concat(cmi_data_dict.values(), axis=1)
        cmi_data.columns = fred_series_cmi.keys()
        
        # Usa ffill per riempire i buchi (es. weekend) ma NON dropna.
        cmi_data.ffill(inplace=True)
        
        print("Dati Macro (CMI) da FRED scaricati con successo.")
    except Exception as e:
        print(f"Errore nel download dei dati FRED: {e}")
        return None, None

    # 2. Download Dati di Mercato da Yahoo Finance
    try:
        market_data = yf.download(market_tickers, start=start_date_mkt, end=end_date, progress=False)
        print("Dati di Mercato da Yahoo Finance scaricati con successo.")
    except Exception as e:
        print(f"Errore nel download dei dati di mercato: {e}")
        return None, None
            
    print("--- Download Dati Completato ---\n")
    return market_data, cmi_data
