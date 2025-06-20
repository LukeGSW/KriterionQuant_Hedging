# bot_runner.py

import configparser
import datetime
import pandas as pd

# Importa le funzioni dai tuoi moduli esistenti e sicuri
from app.dashboard import run_full_strategy
from src.telegram_notifier import send_telegram_message

def run_automated_signal():
    """
    Esegue la logica, estrae l'ultimo segnale e invia la notifica.
    """
    print("Avvio processo di generazione segnale automatico...")
    config = configparser.ConfigParser()
    # Legge sia il file config.ini sia i parametri di default
    config.read('config.ini')
    
    # Carica i parametri della strategia dal config
    params = dict(config['STRATEGY_PARAMS'])
    for key, value in params.items():
        try:
            params[key] = float(value)
        except (ValueError, TypeError):
            pass

    # Carica le credenziali del bot
    bot_token = config.get('TELEGRAM', 'bot_token')
    chat_id = config.get('TELEGRAM', 'chat_id')

    # Eseguiamo la logica su un periodo di tempo sufficiente per calcolare le medie
    # (es. 252 giorni lavorativi per la media del CMI + qualche giorno extra)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=400) 

    print(f"Calcolo segnali dal {start_date} al {end_date}...")
    # Chiama la tua funzione originale che si trova in dashboard.py
    results = run_full_strategy(params, start_date, end_date)

    # Controlla che i risultati siano validi
    if results is None or results[5] is None or results[5].empty:
        error_msg = "ERRORE: Calcolo dei segnali fallito. Nessun dato restituito dalla strategia."
        print(error_msg)
        send_telegram_message(error_msg, bot_token, chat_id)
        return

    # Estrai l'ultimo segnale valido
    df_results = results[5]
    latest_signal = df_results.iloc[-1]
    current_date = latest_signal.name.strftime('%Y-%m-%d')
    signal_cmi = int(latest_signal['Signal_CMI'])
    signal_vix = int(latest_signal['Signal_VIX'])
    signal_count = int(latest_signal['Signal_Count'])

    # Formatta il messaggio (usando la stessa logica del tuo vecchio main.py)
    cmi_status = "🟢 ATTIVO" if signal_cmi == 1 else "🔴 NON ATTIVO"
    vix_status = "🟢 ATTIVO" if signal_vix == 1 else "🔴 NON ATTIVO"

    if signal_count == 0:
        azione = "Nessuna copertura richiesta."
    elif signal_count == 1:
        azione = f"Assumere/Mantenere 1 Tranche di copertura ({params['hedge_percentage_per_tranche'] * 100:.3f}%)."
    else: # signal_count >= 2
        azione = f"Assumere/Mantenere {signal_count} Tranches di copertura ({params['hedge_percentage_per_tranche'] * 100 * signal_count:.3f}%)."

    message = (
        f"**Segnale di Copertura Kriterion - {current_date}** 🔱\n\n"
        f"*- Indicatore CMI*: {cmi_status}\n"
        f"*- Indicatore VIX Ratio*: {vix_status}\n\n"
        f"▶️ **Segnale Composito:** {signal_count} Tranche\n"
        f"💰 **Azione Richiesta:** {azione}"
    )

    print("\n--- Invio Notifica Telegram ---")
    print(message)
    send_telegram_message(message, bot_token, chat_id)

if __name__ == '__main__':
    run_automated_signal()
