# bot_runner.py
# VERSIONE CORRETTA: Sincronizzata con lo stato reale (Active vs Stop Loss)

import configparser
import datetime
import pandas as pd

# Importa le funzioni dai tuoi moduli esistenti
from app.dashboard import run_full_strategy
from src.telegram_notifier import send_telegram_message

def run_automated_signal():
    """
    Esegue la logica, controlla lo stato reale dei contratti (inclusi Stop Loss)
    e invia la notifica corretta.
    """
    print("Avvio processo di generazione segnale automatico S&P...")
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Carica i parametri della strategia dal config
    params = dict(config['STRATEGY_PARAMS'])
    for key, value in params.items():
        try:
            params[key] = float(value)
        except (ValueError, TypeError):
            pass

    # Assicuriamo che lo Stop Loss sia impostato (default 5% se manca)
    if 'stop_loss_threshold_hedge' not in params:
        params['stop_loss_threshold_hedge'] = 0.05

    # Carica le credenziali del bot
    bot_token = config.get('TELEGRAM', 'bot_token')
    chat_id = config.get('TELEGRAM', 'chat_id')

    # Periodo di calcolo
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=400) 

    print(f"Calcolo segnali dal {start_date} al {end_date}...")
    # Esegue la strategia (che ora ritorna df_final con la colonna 'MES_Contracts')
    results = run_full_strategy(params, start_date, end_date)

    # Validazione risultati
    if results is None or results[5] is None or results[5].empty:
        error_msg = "ERRORE: Calcolo dei segnali fallito. Nessun dato restituito dalla strategia."
        print(error_msg)
        send_telegram_message(error_msg, bot_token, chat_id)
        return

    # Estrazione dati ultima candela
    df_results = results[5]
    last = df_results.iloc[-1]
    current_date = last.name.strftime('%Y-%m-%d')
    
    # Indicatori grezzi
    signal_cmi = int(last.get('Signal_CMI', 0))
    signal_vix = int(last.get('Signal_VIX', 0))
    signal_count_raw = int(last.get('Signal_Count', 0))
    
    # --- LOGICA DI CONTROLLO STATO REALE ---
    # Leggiamo i contratti effettivi. Se negativi, siamo Short (Coperti).
    contracts = last.get('MES_Contracts', 0)
    is_hedged_active = contracts < -0.01 # Usiamo una soglia float negativa
    
    # Formattazione stati indicatori
    cmi_status_icon = "🟢" if signal_cmi == 1 else "⚪"
    vix_status_icon = "🟢" if signal_vix == 1 else "⚪"

    # Determinazione Stato Finale e Azione
    if is_hedged_active:
        header_status = "🟢 COPERTURA ATTIVA"
        azione = f"Mantenere {abs(contracts):.2f} contratti Micro ES Short."
    elif signal_count_raw > 0 and not is_hedged_active:
        # C'è segnale ma contratti a 0 -> È scattato lo STOP LOSS
        header_status = "🔴 NON ATTIVO (STOP LOSS)"
        azione = "Posizione chiusa per Stop Loss. Attendere rientro o nuovo segnale."
    else:
        # Nessun segnale
        header_status = "⚪ FLAT"
        azione = "Nessuna copertura richiesta."
    
    dashboard_url = "https://kriterionquanthedging-ftyojbunrcy7wjgsj8ajrc.streamlit.app/"

    message = (
        f"**Segnale Kriterion S&P - {current_date}** 🔱\n\n"
        f"Stato: **{header_status}**\n\n"
        f"*- CMI*: {cmi_status_icon}\n"
        f"*- VIX Ratio*: {vix_status_icon}\n"
        f"*- Segnale Raw*: {signal_count_raw} Tranche\n\n"
        f"📉 **Contratti Reali:** {contracts:.2f}\n"
        f"💡 **Azione:** {azione}\n\n"
        f"⚙️ _SL Impostato: {params['stop_loss_threshold_hedge']*100:.0f}%_\n"
        f"[Apri Dashboard Interattiva]({dashboard_url})"
    )

    print("\n--- Invio Notifica Telegram ---")
    print(message)
    send_telegram_message(message, bot_token, chat_id)

if __name__ == '__main__':
    run_automated_signal()
