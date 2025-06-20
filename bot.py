# bot.py

import os
from datetime import datetime
import yfinance as yf
import plotly.graph_objects as go

# Importiamo le TUE funzioni ESATTE dal TUO file.
# Assicurati che KriterionQuant_Hedging.py sia nella stessa cartella.
from KriterionQuant_Hedging import calcola_cmi, calcola_vix_ratio

# --- IMPOSTAZIONI STRATEGIA E BOT ---
# Puoi modificare questi valori per cambiare il comportamento del bot
SOGLIA_CMI = 1.0
CAPITALE_PER_HEDGING = 100000  # Capitale di riferimento per calcolo tranche
PERCENTUALE_HEDGING = 20         # Percentuale da usare per la copertura
TICKER_HEDGING_ASSET = 'GLD'     # Ticker usato per calcolare il valore del contratto
LINK_STREAMLIT = "https://kriterionquanthedging-ftyojbunrcy7wjgsj8ajrc.streamlit.app/" # Il tuo link

# Crea una cartella per salvare i grafici se non esiste
if not os.path.exists("charts"):
    os.makedirs("charts")

def generare_report_completo():
    """
    Chiama le funzioni originali, calcola tutti i segnali e le tranche,
    genera i grafici e restituisce un report completo.
    """
    print("Avvio generazione report completo...")
    start_date = "2000-01-01"
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    report = {
        "paths_grafici": []
    }

    # 1. Calcolo e Grafico Segnale CMI
    try:
        print("Calcolo segnale CMI...")
        cmi_df = calcola_cmi(start_date=start_date)
        cmi_latest = cmi_df.iloc[-1]
        
        report['segnale_cmi'] = "ATTIVO" if cmi_latest > SOGLIA_CMI else "NON ATTIVO"
        report['valore_cmi'] = round(cmi_latest, 2)
        report['soglia_cmi'] = SOGLIA_CMI
        
        # Genera Grafico CMI
        fig_cmi = go.Figure()
        fig_cmi.add_trace(go.Scatter(x=cmi_df.index, y=cmi_df, name='CMI'))
        fig_cmi.add_hline(y=SOGLIA_CMI, line_dash="dash", line_color="red", annotation_text="Soglia")
        fig_cmi.update_layout(title_text='Segnale CMI (Composite Macro Index)', xaxis_title='Data', yaxis_title='Valore')
        path_cmi = os.path.join("charts", "cmi_signal.png")
        fig_cmi.write_image(path_cmi, width=800, height=500)
        report["paths_grafici"].append(path_cmi)
        print(f"Grafico CMI salvato in {path_cmi}")

    except Exception as e:
        report['segnale_cmi'] = "ERRORE"
        report['errore_cmi'] = str(e)
        print(f"Errore nel calcolo CMI: {e}")

    # 2. Calcolo e Grafico Segnale VIX Ratio
    try:
        print("Calcolo segnale VIX Ratio...")
        vix_df = calcola_vix_ratio(start_date=start_date, end_date=end_date)
        vix_ratio_latest = vix_df['VIX_Ratio'].iloc[-1]
        vix_ma_latest = vix_df['VIX_Ratio_MA'].iloc[-1]

        report['segnale_vix'] = "ATTIVO" if vix_ratio_latest > vix_ma_latest else "NON ATTIVO"
        report['valore_vix_ratio'] = round(vix_ratio_latest, 3)
        report['valore_vix_ma'] = round(vix_ma_latest, 3)

        # Genera Grafico VIX Ratio
        fig_vix = go.Figure()
        fig_vix.add_trace(go.Scatter(x=vix_df.index, y=vix_df['VIX_Ratio'], name='VIX Ratio'))
        fig_vix.add_trace(go.Scatter(x=vix_df.index, y=vix_df['VIX_Ratio_MA'], name='Media Mobile (10 gg)'))
        fig_vix.update_layout(title_text='Segnale VIX Ratio vs Media Mobile', xaxis_title='Data', yaxis_title='Ratio')
        path_vix = os.path.join("charts", "vix_ratio_signal.png")
        fig_vix.write_image(path_vix, width=800, height=500)
        report["paths_grafici"].append(path_vix)
        print(f"Grafico VIX Ratio salvato in {path_vix}")

    except Exception as e:
        report['segnale_vix'] = "ERRORE"
        report['errore_vix'] = str(e)
        print(f"Errore nel calcolo VIX Ratio: {e}")

    # 3. Calcolo Tranche di Copertura
    try:
        print("Calcolo tranche di copertura...")
        prezzo_hedging_asset = yf.Ticker(TICKER_HEDGING_ASSET).history(period='1d')['Close'].iloc[-1]
        valore_punto_micro = 10 # Valore per contratto micro (es. MES, MNQ, MGC per l'oro)
        
        capitale_da_coprire = CAPITALE_PER_HEDGING * (PERCENTUALE_HEDGING / 100)
        valore_contratto_micro = prezzo_hedging_asset * valore_punto_micro
        
        n_contratti = capitale_da_coprire / valore_contratto_micro
        report['tranche_copertura'] = round(n_contratti)
        report['asset_di_copertura'] = TICKER_HEDGING_ASSET
    except Exception as e:
        report['tranche_copertura'] = "ERRORE"
        report['errore_tranche'] = str(e)
        print(f"Errore nel calcolo Tranche: {e}")

    return report

def formatta_messaggio_telegram(report):
    """Crea il testo formattato per il messaggio Telegram."""
    
    # Intestazione
    messaggio = f"*{'Report Segnali Kriterion Quant'}*\n"
    messaggio += f"_{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}_\n"
    messaggio += ("-"*25) + "\n\n"

    # Sezione CMI
    if 'errore_cmi' in report:
        messaggio += f"*Segnale CMI:* {report.get('segnale_cmi', 'N/A')}\n"
        messaggio += f"`Dettagli: {report.get('errore_cmi', '')}`\n\n"
    else:
        messaggio += f"*Segnale CMI:* {report.get('segnale_cmi', 'N/A')}\n"
        messaggio += f"`Valore: {report.get('valore_cmi', 'N/A')} (Soglia: {report.get('soglia_cmi', 'N/A')})`\n\n"

    # Sezione VIX Ratio
    if 'errore_vix' in report:
        messaggio += f"*Segnale VIX Ratio:* {report.get('segnale_vix', 'N/A')}\n"
        messaggio += f"`Dettagli: {report.get('errore_vix', '')}`\n\n"
    else:
        messaggio += f"*Segnale VIX Ratio:* {report.get('segnale_vix', 'N/A')}\n"
        messaggio += f"`Ratio: {report.get('valore_vix_ratio', 'N/A')} (MA: {report.get('valore_vix_ma', 'N/A')})`\n\n"

    # Sezione Tranche
    if 'errore_tranche' in report:
         messaggio += f"*Tranche di Copertura:* {report.get('tranche_copertura', 'N/A')}\n"
         messaggio += f"`Dettagli: {report.get('errore_tranche', '')}`\n\n"
    else:
        messaggio += f"*Tranche di Copertura:*\n"
        messaggio += f"`{report.get('tranche_copertura', 'N/A')} contratti micro {report.get('asset_di_copertura', '')}`\n\n"

    # Link alla Dashboard
    messaggio += ("-"*25) + "\n"
    messaggio += f"[Apri Dashboard Interattiva]({LINK_STREAMLIT})"

    return messaggio


# --- ESECUZIONE PRINCIPALE ---
if __name__ == '__main__':
    # 1. Genera tutti i dati e i grafici
    report_completo = generare_report_completo()

    # 2. Crea il messaggio di testo
    messaggio_testo = formatta_messaggio_telegram(report_completo)
    
    # 3. Stampa tutto a schermo per un controllo finale
    print("\n" + "="*40)
    print("MESSAGGIO PRONTO PER TELEGRAM:")
    print("="*40)
    print(messaggio_testo)
    print("\nGrafici generati e salvati nella cartella 'charts':")
    print(report_completo.get("paths_grafici", "Nessun grafico generato."))
    print("="*40)
    
    # Il prossimo passo sarà inserire qui il codice per inviare `messaggio_testo`
    # e i file dei grafici a Telegram.
