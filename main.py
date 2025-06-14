# src/main.py
import pandas as pd
import datetime as dt
import configparser
import ast # Per leggere il dizionario dal config

from data_fetcher import fetch_all_data
from indicator_calculator import calculate_signals
from telegram_notifier import send_telegram_message

def run_signal_generation():
    """
    Funzione principale che orchestra il processo di generazione e invio del segnale.
    """
    # 1. Carica la configurazione
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Parametri strategia
    cmi_ma_window = config.getint('STRATEGY_PARAMS', 'cmi_ma_window')
    vix_upper = config.getfloat('STRATEGY_PARAMS', 'vix_ratio_upper_threshold')
    vix_lower = config.getfloat('STRATEGY_PARAMS', 'vix_ratio_lower_threshold')
    
    # Ticker
    market_tickers = ['SPY', 'ES=F', '^VIX', '^VIX3M']
    fred_series_str = config.get('DATA', 'fred_series_cmi')

    # Telegram
    bot_token = config.get('TELEGRAM', 'bot_token')
    chat_id = config.get('TELEGRAM', 'chat_id')

    # 2. Scarica i dati
    market_data, cmi_data = fetch_all_data(fred_series_str, market_tickers)
    if market_data is None or cmi_data is None:
        error_msg = "ERRORE: Impossibile scaricare i dati. Esecuzione interrotta."
        print(error_msg)
        send_telegram_message(error_msg, bot_token, chat_id)
        return

    # 3. Calcola i segnali
    df_signals = calculate_signals(market_data, cmi_data, cmi_ma_window, vix_upper, vix_lower)
    
    # 4. Estrai l'ultimo segnale
    latest_signal = df_signals.iloc[-1]
    current_date = latest_signal.name.strftime('%Y-%m-%d')
    signal_cmi = int(latest_signal['Signal_CMI'])
    signal_vix = int(latest_signal['Signal_VIX'])
    signal_count = int(latest_signal['Signal_Count'])

    # 5. Formatta e invia il messaggio
    cmi_status = "🟢 ATTIVO" if signal_cmi == 1 else "🔴 NON ATTIVO"
    vix_status = "🟢 ATTIVO" if signal_vix == 1 else "🔴 NON ATTIVO"
    
    if signal_count == 0:
        azione = "Nessuna copertura richiesta."
    elif signal_count == 1:
        azione = "Assumere/Mantenere 1 Tranche di copertura (87.5%)."
    else: # signal_count == 2
        azione = "Assumere/Mantenere 2 Tranches di copertura (175%)."

    message = (
        f"**Segnale di Copertura Kriterion - {current_date}** 🔱\n\n"
        f"- *Indicatore CMI*: {cmi_status} ({signal_cmi})\n"
        f"- *Indicatore VIX Ratio*: {vix_status} ({signal_vix})\n\n"
        f"▶️ **Segnale Composito:** {signal_count} Tranche\n"
        f"💰 **Azione Richiesta:** {azione}"
    )
    
    print("\n--- Invio Notifica Telegram ---")
    print(message)
    send_telegram_message(message, bot_token, chat_id)

if __name__ == '__main__':
    run_signal_generation()
