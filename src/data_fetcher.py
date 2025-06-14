# src/data_fetcher.py
import pandas as pd
import yfinance as yf
import pandas_datareader.data as web
import datetime as dt
import ast

def fetch_all_data(fred_series_str, market_tickers, start_date_str=None):
    print("--- Inizio Download Dati ---")
    
    fred_series_cmi = ast.literal_eval(fred_series_str)
    
    # Se non viene fornita una data di inizio, scarica gli ultimi 2-3 anni
    if start_date_str is None:
        end_date = pd.to_datetime('today').normalize()
        start_date_mkt = end_date - pd.DateOffset(years=2)
        start_date_cmi = end_date - pd.DateOffset(years=3)
    else:
        # Se fornita, usa quella data per il backtest completo
        start_date_mkt = pd.to_datetime(start_date_str)
        start_date_cmi = pd.to_datetime(start_date_str)
        end_date = pd.to_datetime('today').normalize()

    # ... (il resto del codice rimane uguale)
    try:
        market_data = yf.download(market_tickers, start=start_date_mkt, end=end_date, progress=False)
        if market_data.empty: print("ATTENZIONE: yfinance ha restituito un DataFrame vuoto.")
        else: print("Dati di Mercato da Yahoo Finance scaricati.")
    except Exception as e:
        print(f"Errore critico nel download dei dati di mercato: {e}")
        market_data = pd.DataFrame()

    try:
        cmi_data_dict = {}
        for name, ticker in fred_series_cmi.items():
            cmi_data_dict[name] = web.DataReader(ticker, 'fred', start_date_cmi, end_date)
        cmi_data = pd.concat(cmi_data_dict.values(), axis=1)
        cmi_data.columns = fred_series_cmi.keys()
        cmi_data.ffill(inplace=True)
        if cmi_data.empty: print("ATTENZIONE: pandas_datareader ha restituito un DataFrame vuoto.")
        else: print("Dati Macro (CMI) da FRED scaricati.")
    except Exception as e:
        print(f"Errore critico nel download dei dati CMI: {e}")
        cmi_data = pd.DataFrame()
            
    print("--- Download Dati Completato ---\n")
    return market_data, cmi_data
