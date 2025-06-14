# src/telegram_notifier.py
import requests

def send_telegram_message(message, token, chat_id):
    """
    Invia un messaggio a un chat/canale Telegram.
    """
    # TODO: Implementare la logica completa con la libreria python-telegram-bot
    # Per ora, usiamo una semplice richiesta HTTP per inviare il messaggio.
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Messaggio inviato con successo a Telegram.")
        else:
            print(f"Errore nell'invio a Telegram: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Errore di connessione a Telegram: {e}")
