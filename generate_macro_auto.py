#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NexusGoldOne — Generatore automatico Report Macro & Geopolitica
Gira ogni lunedì su GitHub Actions e invia il PDF al canale Telegram.
Versione 2.0 — Analisi AI dinamica via Claude API + prezzi live + notizie RSS
"""

import os
import json
import re
import requests
from datetime import date, datetime, timedelta, timezone

# ── DATE AUTOMATICHE ──────────────────────────────────────────────────────────
today    = date.today()
monday   = today - timedelta(days=today.weekday())
friday   = monday + timedelta(days=4)   # i mercati vanno lun-ven

MESI = {
    1:"Gennaio", 2:"Febbraio", 3:"Marzo", 4:"Aprile",
    5:"Maggio", 6:"Giugno", 7:"Luglio", 8:"Agosto",
    9:"Settembre", 10:"Ottobre", 11:"Novembre", 12:"Dicembre"
}
MESI_SHORT = {
    1:"Gen", 2:"Feb", 3:"Mar", 4:"Apr", 5:"Mag", 6:"Giu",
    7:"Lug", 8:"Ago", 9:"Set", 10:"Ott", 11:"Nov", 12:"Dic"
}

WEEK_LABEL = f"Settimana dal {monday.day:02d} al {friday.day:02d} {MESI[friday.month]} {friday.year}"
WEEK_SHORT = f"{monday.day:02d} {MESI_SHORT[monday.month]} – {friday.day:02d} {MESI_SHORT[friday.month]} {friday.year}"
FILENAME   = f"MACRO_Geopolitica_{monday.strftime('%d-%m-%Y')}.pdf"
OUTPUT     = f"/tmp/{FILENAME}"

# ── NOTIZIE AUTOMATICHE DA RSS FEEDS ─────────────────────────────────────────
def get_weekly_news():
    try:
        import feedparser
    except ImportError:
        print("feedparser non installato, saltando notizie.")
        return []

    feeds = [
        ("Kitco Gold News",    "https://www.kitco.com/rss/kitconews.rss"),
        ("Reuters Markets",    "https://feeds.reuters.com/reuters/businessNews"),
        ("Yahoo Finance",      "https://finance.yahoo.com/rss/topstories"),
        ("MarketWatch",        "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines"),
        ("CNBC Finance",       "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
        ("Investing.com Gold", "https://www.investing.com/rss/news_301.rss"),
    ]

    KEYWORDS_HIGH = [
        'gold', 'xau', 'federal reserve', 'fed rate', 'inflation', 'cpi', 'pce',
        'war', 'attack', 'strike', 'conflict', 'crisis', 'nuclear',
        'china', 'russia', 'iran', 'middle east', 'ukraine', 'taiwan',
        'central bank', 'brics', 'de-dollarization', 'dollar', 'dxy',
        'sanctions', 'tariff', 'trade war', 'recession', 'oil price',
        'goldman sachs gold', 'ubs gold', 'interest rate', 'rate cut', 'rate hike',
        'powell', 'opec', 'ceasefire', 'geopolitical', 'debt ceiling'
    ]
    KEYWORDS_MED = [
        'market', 'stocks', 'sp500', 'nasdaq', 'euro', 'treasury',
        'jobs', 'unemployment', 'gdp', 'economy', 'silver', 'copper',
        'bank', 'ecb', 'boe', 'imf', 'world bank', 'commodity'
    ]

    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=8)

    for source_name, url in feeds:
        try:
            feed = feedparser.parse(url, request_headers={
                'User-Agent': 'Mozilla/5.0 (NexusGoldOne Report Bot/1.0)'
            })
            for entry in feed.entries[:30]:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass

                if pub_date and pub_date < cutoff:
                    continue

                title   = entry.get('title', '').strip()
                summary = entry.get('summary', entry.get('description', '')).strip()
                summary = re.sub(r'<[^>]+>', '', summary)[:250]
                text_low = (title + ' ' + summary).lower()

                score = 0
                for kw in KEYWORDS_HIGH:
                    if kw in text_low:
                        score += 3
                for kw in KEYWORDS_MED:
                    if kw in text_low:
                        score += 1

                if score >= 3:
                    date_str = pub_date.strftime('%d %b') if pub_date else '—'
                    impact   = '🔴 CRITICO' if score >= 9 else ('🟠 ALTO' if score >= 5 else '🟡 MEDIO')
                    articles.append({
                        'title':    title,
                        'source':   source_name,
                        'score':    score,
                        'impact':   impact,
                        'summary':  summary[:180],
                        'date_str': date_str,
                    })
        except Exception as e:
            print(f"Errore feed {source_name}: {e}")

    articles.sort(key=lambda x: x['score'], reverse=True)

    seen = set()
    unique = []
    for art in articles:
        norm = re.sub(r'\W+', ' ', art['title'].lower()).strip()
        words = set(norm.split())
        is_dup = False
        for s in seen:
            sw = set(s.split())
            overlap = len(words & sw) / max(len(words), len(sw), 1)
            if overlap > 0.65:
                is_dup = True
                break
        if not is_dup and len(art['title']) > 10:
            seen.add(norm)
            unique.append(art)
        if len(unique) >= 7:
            break

    print(f"Notizie trovate: {len(unique)}")
    return unique

print("Recupero notizie della settimana...")
weekly_news = get_weekly_news()

# ── PREZZI LIVE (Yahoo Finance) ───────────────────────────────────────────────
def get_price(ticker):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty:
            return None, None, None, None
        close_last = hist["Close"].iloc[-1]
        close_prev = hist["Close"].iloc[0]
        change_pct = ((close_last - close_prev) / close_prev) * 100
        week_low   = hist["Low"].min()
        week_high  = hist["High"].max()
        return close_last, change_pct, week_low, week_high
    except Exception as e:
        print(f"Errore prezzo {ticker}: {e}")
        return None, None, None, None

print("Recupero prezzi di mercato...")
xau_price, xau_chg, xau_low, xau_high = get_price("GC=F")
spx_price, spx_chg, spx_low, spx_high = get_price("^GSPC")
ndx_price, ndx_chg, ndx_low, ndx_high = get_price("^IXIC")
dxy_price, dxy_chg, dxy_low, dxy_high = get_price("DX-Y.NYB")

def fmt(val, decimals=0, prefix=""):
    if val is None: return "N/D"
    return f"{prefix}{val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_chg(val):
    if val is None: return "N/D"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%".replace(".", ",")

xau_row = ["XAU/USD (Oro)",     f"~${fmt(xau_price, 0)}", fmt_chg(xau_chg), f"${fmt(xau_low, 0)} / ${fmt(xau_high, 0)}"]
spx_row = ["S&P 500",           f"~{fmt(spx_price, 0)}",  fmt_chg(spx_chg), f"{fmt(spx_low, 0)} / {fmt(spx_high, 0)}"]
ndx_row = ["NASDAQ Composite",  f"~{fmt(ndx_price, 0)}",  fmt_chg(ndx_chg), f"{fmt(ndx_low, 0)} / {fmt(ndx_high, 0)}"]
dxy_row = ["DXY (Dollaro USA)", f"~{fmt(dxy_price, 2)}",  fmt_chg(dxy_chg), f"{fmt(dxy_low, 2)} / {fmt(dxy_high, 2)}"]

# ── ANALISI AI DINAMICA (Claude Haiku) ───────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ai = None

if ANTHROPIC_API_KEY:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Prepara lista notizie per il prompt
        news_text = ""
        if weekly_news:
            news_text = "\n\nNOTIZIE REALI DELLA SETTIMANA (da feed RSS finanziari):\n"
            for i, n in enumerate(weekly_news[:7], 1):
                news_text += f"{i}. [{n['impact']}] {n['title']} ({n['source']}, {n['date_str']})\n"

        lun = monday
        mar = monday + timedelta(days=1)
        mer = monday + timedelta(days=2)
        gio = monday + timedelta(days=3)
        ven = monday + timedelta(days=4)

        prompt = f"""Sei l'analista macro di NexusGoldOne, servizio professionale di copytrading sull'oro (XAU/USD).
Oggi e' {today.strftime('%A %d %B %Y')} — stai scrivendo il report settimanale.

DATI DI MERCATO REALI (aggiornati a oggi):
- XAU/USD (Oro): ${fmt(xau_price, 0)} | Var. settimanale: {fmt_chg(xau_chg)} | Range: ${fmt(xau_low,0)}-${fmt(xau_high,0)}
- S&P 500: {fmt(spx_price, 0)} | Var. settimanale: {fmt_chg(spx_chg)} | Range: {fmt(spx_low,0)}-{fmt(spx_high,0)}
- NASDAQ: {fmt(ndx_price, 0)} | Var. settimanale: {fmt_chg(ndx_chg)} | Range: {fmt(ndx_low,0)}-{fmt(ndx_high,0)}
- DXY: {fmt(dxy_price, 2)} | Var. settimanale: {fmt_chg(dxy_chg)} | Range: {fmt(dxy_low,2)}-{fmt(dxy_high,2)}
{news_text}

Settimana corrente: Lun {lun.day} {MESI_SHORT[lun.month]}, Mar {mar.day}, Mer {mer.day}, Gio {gio.day}, Ven {ven.day} {MESI_SHORT[ven.month]} {ven.year}

Genera un'analisi macro-geopolitica AGGIORNATA e SPECIFICA per {today.strftime('%B %Y')}.
Basa l'analisi sulle notizie reali ricevute. Tono professionale per investitori retail sull'oro.
Tutto in italiano. Nei testi usa tag HTML <b>Titolo:</b> per i bullet. Niente markdown.

Rispondi SOLO con JSON valido, nessun testo fuori:
{{
  "snapshot_commento": "2-3 frasi tecniche sui prezzi reali di questa settimana, citando i valori esatti",
  "geopolitica_intro": "3-4 frasi sulla situazione geopolitica ATTUALE di {today.strftime('%B %Y')}, basata sulle notizie reali",
  "geo_bullet_1": "<b>Tema 1:</b> evento geopolitico specifico e reale con dettagli aggiornati",
  "geo_bullet_2": "<b>Tema 2:</b> evento geopolitico specifico aggiornato",
  "geo_bullet_3": "<b>Tema 3:</b> evento geopolitico specifico aggiornato",
  "geo_bullet_4": "<b>Tema 4:</b> evento geopolitico specifico aggiornato",
  "azionario_intro": "2-3 frasi sui mercati azionari USA nel contesto attuale",
  "sp500_bullet_1": "<b>Livelli chiave:</b> supporti e resistenze S&P500 con valori numerici reali",
  "sp500_bullet_2": "<b>Rischi principali:</b> rischi specifici e attuali",
  "sp500_bullet_3": "<b>Opportunita':</b> opportunita' specifiche nel contesto attuale",
  "ndx_bullet_1": "<b>Chiusura settimana precedente:</b> {fmt(ndx_price, 0)} ({fmt_chg(ndx_chg)}). Commento sul movimento",
  "ndx_bullet_2": "<b>Driver positivi:</b> fattori positivi specifici attuali per il NASDAQ",
  "ndx_bullet_3": "<b>Rischio:</b> rischi specifici attuali per il settore tech",
  "dedollarizzazione_intro": "2-3 frasi aggiornate su de-dollarizzazione e acquisti banche centrali con dati reali {today.strftime('%B %Y')}",
  "cb_cina_acquisti": "valore aggiornato es. ~XX t/mese",
  "cb_cina_riserve": "valore aggiornato es. X.XXX+ t",
  "cb_cina_trend": "trend aggiornato Cina 1-2 parole",
  "cb_india_acquisti": "valore aggiornato es. ~XX t/mese",
  "cb_india_riserve": "valore aggiornato es. XXX+ t",
  "cb_india_trend": "trend aggiornato India 1-2 parole",
  "cb_brics_acquisti": "valore aggregato aggiornato",
  "cb_brics_riserve": "percentuale aggiornata riserve globali",
  "cb_brics_trend": "confronto storico aggiornato",
  "cb_global_acquisti": "previsione anno {today.year}",
  "cb_global_riserve": "totale riserve globali aggiornato",
  "cb_global_trend": "dato comparativo aggiornato",
  "dazi_intro": "2-3 frasi sui dazi USA aggiornate a {today.strftime('%B %Y')} con misure reali in vigore",
  "dazi_bullet_1": "<b>Inflazione USA:</b> impatto reale dazi su PCE/CPI con dati attuali",
  "dazi_bullet_2": "<b>Azionario:</b> settori piu' colpiti con dati specifici",
  "dazi_bullet_3": "<b>Oro:</b> come i dazi supportano strutturalmente XAU/USD",
  "dazi_bullet_4": "<b>Opportunita':</b> come l'investitore puo' trarne vantaggio",
  "fed_bullet_1": "<b>Tassi:</b> range ATTUALE Fed con percentuale esatta e decisione piu' recente",
  "fed_bullet_2": "<b>Prossima decisione:</b> data esatta prossima riunione FOMC e attese mercato",
  "fed_bullet_3": "<b>Attenzione:</b> dati macro specifici determinanti per il prossimo meeting",
  "fed_bullet_4": "<b>Nota:</b> tema rilevante attuale su Fed o leadership",
  "bce_bullet_1": "<b>Tassi BCE:</b> livello attuale e decisione recente con data",
  "bce_bullet_2": "<b>Prossima riunione:</b> data esatta e scenario atteso",
  "cal_lun_evento": "dato/evento macro specifico e reale del lunedi'",
  "cal_lun_mercati": "mercati impattati",
  "cal_lun_imp": "🟠 Alta",
  "cal_mar_evento": "dato/evento macro specifico del martedi'",
  "cal_mar_mercati": "mercati impattati",
  "cal_mar_imp": "🟠 Alta",
  "cal_mer_evento": "dato/evento macro specifico del mercoledi'",
  "cal_mer_mercati": "mercati impattati",
  "cal_mer_imp": "🔴 Critica",
  "cal_gio_evento": "dato/evento macro specifico del giovedi'",
  "cal_gio_mercati": "mercati impattati",
  "cal_gio_imp": "🟠 Alta",
  "cal_ven_evento": "dato/evento macro specifico del venerdi'",
  "cal_ven_mercati": "mercati impattati",
  "cal_ven_imp": "🟡 Media",
  "cal_nota": "nota specifica sul dato piu' importante della settimana con spiegazione dell'impatto",
  "outlook_intro": "2-3 frasi sull'outlook per l'oro con riferimenti ai prezzi reali e al contesto attuale",
  "outlook_bullet_1": "<b>XAU/USD:</b> supporto area $X.XXX, resistenza area $X.XXX. Scenario e proiezione specifica",
  "outlook_bullet_2": "<b>S&P 500:</b> livelli chiave specifici e scenario per la settimana",
  "outlook_bullet_3": "<b>Dati macro USA:</b> dato piu' importante della settimana e impatto atteso su Fed e oro",
  "outlook_bullet_4": "<b>Target analisti oro {today.year}:</b> previsioni aggiornate di almeno 3 banche con cifre reali",
  "outlook_bullet_5": "<b>Scenario base:</b> visione complessiva e bias direzionale per la settimana"
}}"""

        print("Generazione analisi con Claude AI...")
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        ai = json.loads(raw)
        print("Analisi AI generata con successo!")

    except Exception as e:
        print(f"Errore Claude API: {e}. Uso testo di fallback.")
        ai = None

# ── FALLBACK testo statico se Claude non disponibile ─────────────────────────
if ai is None:
    ai = {
        "snapshot_commento": f"L'oro (XAU/USD) chiude la settimana a ${fmt(xau_price, 0)} ({fmt_chg(xau_chg)}), mantenendo la sua traiettoria strutturalmente rialzista. S&P 500 a {fmt(spx_price, 0)} ({fmt_chg(spx_chg)}) e DXY a {fmt(dxy_price, 2)} ({fmt_chg(dxy_chg)}) completano il quadro macro settimanale.",
        "geopolitica_intro": "Il quadro geopolitico internazionale continua a sostenere la domanda di beni rifugio. Le tensioni in Medio Oriente, le manovre nello Stretto di Taiwan e la guerra commerciale USA-Cina mantengono elevata l'incertezza strutturale sui mercati globali.",
        "geo_bullet_1": "<b>Medio Oriente:</b> situazione in evoluzione. Monitorare sviluppi su infrastrutture energetiche e approvvigionamento petrolifero globale.",
        "geo_bullet_2": "<b>USA-Cina:</b> tensioni commerciali e militari nello Stretto di Taiwan. Impatto sulle catene di fornitura dei semiconduttori.",
        "geo_bullet_3": "<b>Guerra commerciale:</b> dazi USA mantengono pressione sull'inflazione globale e incertezza normativa.",
        "geo_bullet_4": "<b>De-dollarizzazione:</b> BRICS+ accelera la diversificazione dalle riserve in dollari verso l'oro fisico.",
        "azionario_intro": "I mercati azionari USA navigano in un contesto di dati macro contrastanti. La stagione degli utili e le aspettative Fed rimangono i principali driver di breve termine.",
        "sp500_bullet_1": f"<b>Livelli chiave:</b> chiusura settimana precedente {spx_row[1]} ({spx_row[2]}). Supporto in area {fmt(spx_low, 0)}, resistenza in area {fmt(spx_high, 0)}.",
        "sp500_bullet_2": "<b>Rischi principali:</b> dazi su farmaci e manifatturiero comprimono i margini aziendali. Volatilita' settoriale elevata.",
        "sp500_bullet_3": "<b>Opportunita':</b> dati macro positivi e utili sopra attese potrebbero supportare i livelli attuali.",
        "ndx_bullet_1": f"<b>Chiusura settimana precedente:</b> {ndx_row[1]} ({ndx_row[2]}). Settore tech in movimento.",
        "ndx_bullet_2": "<b>Driver positivi:</b> aspettative utili solide per i principali titoli tecnologici.",
        "ndx_bullet_3": "<b>Rischio:</b> tensioni geopolitiche e catene di fornitura semiconduttori.",
        "dedollarizzazione_intro": "La domanda strutturale di oro da parte delle banche centrali rimane il pilastro del bull market del metallo. La diversificazione delle riserve dal dollaro verso l'oro fisico continua ad accelerare.",
        "cb_cina_acquisti": "~25 t/mese", "cb_cina_riserve": "2.257+ t", "cb_cina_trend": "Acquisti consecutivi",
        "cb_india_acquisti": "~18 t/mese", "cb_india_riserve": "822+ t", "cb_india_trend": "Diversificazione USD",
        "cb_brics_acquisti": "~60 t/mese", "cb_brics_riserve": "17,4% riserve glob.", "cb_brics_trend": "Era 11,2% nel 2019",
        "cb_global_acquisti": f"~850 t (anno {today.year})", "cb_global_riserve": "~36.000 t totali", "cb_global_trend": "Domanda ai massimi storici",
        "dazi_intro": "La strategia tariffaria USA mantiene pressione sulle catene di fornitura globali e sull'inflazione. L'incertezza normativa rende difficile per i mercati prezzare correttamente il rischio.",
        "dazi_bullet_1": "<b>Inflazione USA:</b> i dazi mantengono il PCE sopra il target Fed del 2%, riducendo lo spazio per tagli dei tassi.",
        "dazi_bullet_2": "<b>Azionario:</b> volatilita' settoriale elevata in auto, farmaceutico e manifatturiero. Margini compressi.",
        "dazi_bullet_3": "<b>Oro:</b> il contesto inflazionistico e l'incertezza creati dai dazi costituiscono supporto strutturale per XAU/USD.",
        "dazi_bullet_4": "<b>Opportunita':</b> ogni escalation commerciale aumenta la domanda di asset rifugio.",
        "fed_bullet_1": "<b>Tassi:</b> range attuale confermato. Politica monetaria restrittiva in corso.",
        "fed_bullet_2": "<b>Prossima decisione:</b> prossima riunione FOMC in programma. Mercati attendono segnali sul percorso dei tassi.",
        "fed_bullet_3": "<b>Attenzione:</b> dati CPI e PCE determinanti per il percorso dei tassi.",
        "fed_bullet_4": "<b>Nota:</b> dichiarazioni dei membri Fed da monitorare per forward guidance.",
        "bce_bullet_1": "<b>Tassi BCE:</b> politica monetaria in modalita' attendista.",
        "bce_bullet_2": "<b>Prossima riunione:</b> prossima decisione BCE in programma.",
        "cal_lun_evento": "Apertura mercati / aggiornamento geopolitica", "cal_lun_mercati": "Oro, Indici", "cal_lun_imp": "🟠 Alta",
        "cal_mar_evento": "Dati manifatturiero / dichiarazioni Fed", "cal_mar_mercati": "Dollaro, Oro", "cal_mar_imp": "🟠 Alta",
        "cal_mer_evento": "CPI USA / Scorte petrolio EIA", "cal_mer_mercati": "Fed, Dollaro, Oro", "cal_mer_imp": "🔴 Critica",
        "cal_gio_evento": "PPI USA / Sussidi disoccupazione settimanali", "cal_gio_mercati": "Dollaro, Oro", "cal_gio_imp": "🟠 Alta",
        "cal_ven_evento": "Sentiment consumatori / Dichiarazioni BCE", "cal_ven_mercati": "Euro, S&P 500, Oro", "cal_ven_imp": "🟡 Media",
        "cal_nota": "Il dato CPI del mercoledi' e' tipicamente il piu' atteso della settimana. Una lettura sopra le attese aumenta la probabilita' di un rinvio dei tagli Fed.",
        "outlook_intro": "Il quadro macro-geopolitico rimane strutturalmente favorevole all'oro nel medio termine. La domanda delle banche centrali e le tensioni geopolitiche costituiscono un floor robusto per XAU/USD.",
        "outlook_bullet_1": f"<b>XAU/USD:</b> supporto in area ${fmt(xau_low, 0)}, resistenza principale in area ${fmt(xau_high, 0)}. Bias rialzista strutturale confermato.",
        "outlook_bullet_2": f"<b>S&P 500:</b> area {fmt(spx_low, 0)} come supporto chiave della settimana.",
        "outlook_bullet_3": "<b>Dati macro USA:</b> CPI e PPI determinanti per le aspettative Fed. Lettura sopra attese = opportunita' di acquisto nel medio termine.",
        "outlook_bullet_4": f"<b>Target analisti oro {today.year}:</b> consenso rialzista tra le principali banche d'investimento con target ambiziosi per fine anno.",
        "outlook_bullet_5": "<b>Scenario base:</b> consolidamento sopra i supporti con possibili spike di volatilita'. Bias strutturale rialzista confermato."
    }

# ── PDF ───────────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, PageBreak,
                                 CondPageBreak)

GOLD       = colors.HexColor('#C9A84C')
DARK_NAVY  = colors.HexColor('#2C3E50')
LIGHT_GRAY = colors.HexColor('#F7F7F7')
MID_GRAY   = colors.HexColor('#D5D8DC')
DARK_GRAY  = colors.HexColor('#666666')
TEXT_COLOR = colors.HexColor('#1A1A1A')
RED_IMPACT = colors.HexColor('#C0392B')
ORG_IMPACT = colors.HexColor('#E67E22')
YEL_IMPACT = colors.HexColor('#D4AC0D')
PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm
CW = PAGE_W - 2 * MARGIN

def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(MID_GRAY); canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H - 1.3*cm, PAGE_W - MARGIN, PAGE_H - 1.3*cm)
    canvas.setFont('Helvetica-Bold', 8); canvas.setFillColor(DARK_GRAY)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.0*cm, "NexusGoldOne")
    canvas.line(MARGIN, 1.8*cm, PAGE_W - MARGIN, 1.8*cm)
    canvas.setFont('Helvetica', 7); canvas.setFillColor(DARK_GRAY)
    canvas.drawCentredString(PAGE_W/2, 1.2*cm,
        f"NexusGoldOne — Report Macro & Geopolitica  |  {WEEK_SHORT}  |  Pag. {doc.page}")
    canvas.restoreState()

def S(h): return Spacer(1, h*cm)

def sec(title):
    return [
        Paragraph(title, ParagraphStyle('sh', fontName='Helvetica-Bold', fontSize=13,
            textColor=TEXT_COLOR, spaceBefore=0.3*cm, spaceAfter=0.08*cm)),
        HRFlowable(width=CW, thickness=0.8, color=colors.HexColor('#BDC3C7'), spaceAfter=0.2*cm)
    ]

def sub(title):
    return Paragraph(title, ParagraphStyle('sub', fontName='Helvetica-Bold', fontSize=10,
        textColor=GOLD, spaceBefore=0.2*cm, spaceAfter=0.06*cm))

def body(text):
    return Paragraph(text, ParagraphStyle('body', fontName='Helvetica', fontSize=9.5,
        textColor=TEXT_COLOR, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=0.10*cm))

def bul(text):
    return Paragraph(f'• {text}', ParagraphStyle('bul', fontName='Helvetica', fontSize=9.5,
        textColor=TEXT_COLOR, leading=14.5,
        leftIndent=0.7*cm, firstLineIndent=-0.35*cm, spaceAfter=0.10*cm))

def tbl(data, widths=None):
    n = len(data[0])
    if widths is None: widths = [CW/n]*n
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),DARK_NAVY), ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,0),9),
        ('ALIGN',(0,0),(-1,0),'CENTER'), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, LIGHT_GRAY]),
        ('FONTNAME',(0,1),(-1,-1),'Helvetica'), ('FONTSIZE',(0,1),(-1,-1),9),
        ('ALIGN',(1,1),(-1,-1),'CENTER'), ('ALIGN',(0,1),(0,-1),'LEFT'),
        ('TOPPADDING',(0,0),(-1,-1),6), ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),8), ('RIGHTPADDING',(0,0),(-1,-1),8),
        ('GRID',(0,0),(-1,-1),0.5,MID_GRAY), ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#BDC3C7')),
    ]))
    return t

def news_tbl(articles):
    if not articles:
        return body("Nessuna notizia di alto impatto rilevata questa settimana dai feed monitorati.")
    rows = [['Imp.', 'Data', 'Titolo (EN)', 'Fonte']]
    impact_colors = []
    for art in articles:
        rows.append([
            art['impact'],
            art['date_str'],
            art['title'][:90] + ('...' if len(art['title']) > 90 else ''),
            art['source']
        ])
        if '🔴' in art['impact']:
            impact_colors.append(RED_IMPACT)
        elif '🟠' in art['impact']:
            impact_colors.append(ORG_IMPACT)
        else:
            impact_colors.append(YEL_IMPACT)
    t = Table(rows, colWidths=[CW*0.12, CW*0.09, CW*0.55, CW*0.24])
    style = [
        ('BACKGROUND',(0,0),(-1,0),DARK_NAVY), ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,0),8.5),
        ('ALIGN',(0,0),(-1,0),'CENTER'), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('FONTNAME',(0,1),(-1,-1),'Helvetica'), ('FONTSIZE',(0,1),(-1,-1),8),
        ('ALIGN',(0,1),(1,-1),'CENTER'), ('ALIGN',(2,1),(3,-1),'LEFT'),
        ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),6), ('RIGHTPADDING',(0,0),(-1,-1),6),
        ('GRID',(0,0),(-1,-1),0.4,MID_GRAY), ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#BDC3C7')),
        ('WORDWRAP',(2,1),(2,-1),'LTR'),
    ]
    for i, ic in enumerate(impact_colors):
        row = i + 1
        bg = LIGHT_GRAY if i % 2 == 1 else colors.white
        style.append(('ROWBACKGROUNDS', (0,row), (-1,row), [bg]))
        style.append(('TEXTCOLOR', (0,row), (0,row), ic))
        style.append(('FONTNAME', (0,row), (0,row), 'Helvetica-Bold'))
        style.append(('FONTSIZE', (0,row), (0,row), 8))
    t.setStyle(TableStyle(style))
    return t

# ── COSTRUZIONE STORY ─────────────────────────────────────────────────────────
story = []

# TITOLO
story.append(S(0.1))
story.append(Paragraph("NEXUSGOLDONE", ParagraphStyle('brand', fontName='Helvetica-Bold',
    fontSize=11, textColor=GOLD, alignment=TA_CENTER, spaceAfter=4)))
story.append(Paragraph("REPORT MACRO &amp; GEOPOLITICA", ParagraphStyle('maintitle',
    fontName='Helvetica-Bold', fontSize=26, textColor=TEXT_COLOR,
    alignment=TA_CENTER, leading=32, spaceAfter=0)))
story.append(S(0.15))
story.append(Paragraph(WEEK_LABEL, ParagraphStyle('weeklabel', fontName='Helvetica-Oblique',
    fontSize=11, textColor=GOLD, alignment=TA_CENTER, spaceAfter=0)))
story.append(S(0.2))
story.append(HRFlowable(width=CW, thickness=1.5, color=GOLD, spaceAfter=0))
story.append(S(0.2))

# SEZ 1 — SNAPSHOT PREZZI
story.extend(sec("1. Snapshot Prezzi Settimanale"))
price_data = [
    ['Asset', 'Chiusura sett. prec.', 'Var. sett. prec.', 'Min / Max settim.'],
    xau_row, spx_row, ndx_row, dxy_row,
]
story.append(tbl(price_data, [CW*0.30, CW*0.22, CW*0.18, CW*0.30]))
story.append(S(0.1))
story.append(body(ai["snapshot_commento"]))

# SEZ 2 — NOTIZIE
story.extend(sec("2. Notizie Piu' Impattanti della Settimana"))
story.append(body(
    "Le notizie sotto riportate sono selezionate automaticamente dai principali feed finanziari internazionali "
    "(Reuters, Kitco Gold News, Yahoo Finance, CNBC, MarketWatch) e classificate per impatto su oro, "
    "dollaro e mercati globali. I titoli sono nella lingua originale (inglese)."
))
story.append(S(0.08))
story.append(news_tbl(weekly_news))
story.append(S(0.1))
story.append(body(
    "<b>Come leggere l'impatto:</b> "
    "<b>🔴 CRITICO</b> = evento che puo' muovere l'oro di $30-100+ in poche ore. "
    "<b>🟠 ALTO</b> = notizia che influenza direttamente le aspettative di mercato. "
    "<b>🟡 MEDIO</b> = contesto macro rilevante da monitorare."
))
story.append(PageBreak())

# SEZ 3 — GEOPOLITICA
story.extend(sec("3. Geopolitica — Scenario Globale"))
story.append(body(ai["geopolitica_intro"]))
story.append(bul(ai["geo_bullet_1"]))
story.append(bul(ai["geo_bullet_2"]))
story.append(bul(ai["geo_bullet_3"]))
story.append(bul(ai["geo_bullet_4"]))

# SEZ 4 — MERCATI AZIONARI
story.extend(sec("4. Mercati Azionari — NASDAQ e S&amp;P 500"))
story.append(body(ai["azionario_intro"]))
story.append(sub("S&amp;P 500"))
story.append(bul(ai["sp500_bullet_1"]))
story.append(bul(ai["sp500_bullet_2"]))
story.append(bul(ai["sp500_bullet_3"]))
story.append(sub("NASDAQ Composite"))
story.append(bul(ai["ndx_bullet_1"]))
story.append(bul(ai["ndx_bullet_2"]))
story.append(bul(ai["ndx_bullet_3"]))
story.append(PageBreak())

# SEZ 5 — DE-DOLLARIZZAZIONE
story.extend(sec("5. De-Dollarizzazione e Acquisti Banche Centrali"))
story.append(body(ai["dedollarizzazione_intro"]))
cb_data = [
    ['Paese / Banca',     'Acquisti mensili',       'Riserve totali',          'Trend'],
    ['Cina (PBOC)',       ai["cb_cina_acquisti"],    ai["cb_cina_riserve"],     ai["cb_cina_trend"]],
    ['India (RBI)',       ai["cb_india_acquisti"],   ai["cb_india_riserve"],    ai["cb_india_trend"]],
    ['BRICS+ (aggreg.)', ai["cb_brics_acquisti"],   ai["cb_brics_riserve"],    ai["cb_brics_trend"]],
    ['Globale (prev.)',  ai["cb_global_acquisti"],  ai["cb_global_riserve"],   ai["cb_global_trend"]],
]
story.append(tbl(cb_data, [CW*0.27, CW*0.21, CW*0.24, CW*0.28]))
story.append(S(0.1))

# SEZ 6 — DAZI
story.extend(sec("6. Dazi USA e Guerra Commerciale"))
story.append(body(ai["dazi_intro"]))
story.append(bul(ai["dazi_bullet_1"]))
story.append(bul(ai["dazi_bullet_2"]))
story.append(bul(ai["dazi_bullet_3"]))
story.append(bul(ai["dazi_bullet_4"]))

# SEZ 7 — BANCHE CENTRALI
story.extend(sec("7. Banche Centrali — Fed &amp; BCE"))
story.append(sub("Federal Reserve (USA)"))
story.append(bul(ai["fed_bullet_1"]))
story.append(bul(ai["fed_bullet_2"]))
story.append(bul(ai["fed_bullet_3"]))
story.append(bul(ai["fed_bullet_4"]))
story.append(sub("Banca Centrale Europea (BCE)"))
story.append(bul(ai["bce_bullet_1"]))
story.append(bul(ai["bce_bullet_2"]))
# CondPageBreak: va a pagina nuova solo se rimangono meno di 9cm — evita pagina bianca finale
story.append(CondPageBreak(9*cm))

# SEZ 8 — CALENDARIO
lun = monday
mar = monday + timedelta(days=1)
mer = monday + timedelta(days=2)
gio = monday + timedelta(days=3)
ven = monday + timedelta(days=4)
def gf(d): return f"{d.strftime('%a')} {d.day} {MESI_SHORT[d.month]}"

story.extend(sec(f"8. Calendario Notizie — {WEEK_LABEL}"))
story.append(body(
    "Le principali pubblicazioni macroeconomiche e gli eventi geopolitici da monitorare questa settimana. "
    "I dati ad alto impatto possono generare movimenti significativi su oro, dollaro e indici azionari."
))
cal_data = [
    ['Data', 'Evento', 'Mercati', 'Importanza'],
    [gf(lun), ai["cal_lun_evento"], ai["cal_lun_mercati"], ai["cal_lun_imp"]],
    [gf(mar), ai["cal_mar_evento"], ai["cal_mar_mercati"], ai["cal_mar_imp"]],
    [gf(mer), ai["cal_mer_evento"], ai["cal_mer_mercati"], ai["cal_mer_imp"]],
    [gf(gio), ai["cal_gio_evento"], ai["cal_gio_mercati"], ai["cal_gio_imp"]],
    [gf(ven), ai["cal_ven_evento"], ai["cal_ven_mercati"], ai["cal_ven_imp"]],
]
story.append(tbl(cal_data, [CW*0.16, CW*0.38, CW*0.25, CW*0.21]))
story.append(S(0.1))
story.append(body(f"<b>Nota:</b> {ai['cal_nota']}"))
story.append(S(0.1))

# SEZ 9 — OUTLOOK
story.extend(sec(f"9. Outlook — {WEEK_LABEL}"))
story.append(body(ai["outlook_intro"]))
story.append(bul(ai["outlook_bullet_1"]))
story.append(bul(ai["outlook_bullet_2"]))
story.append(bul(ai["outlook_bullet_3"]))
story.append(bul(ai["outlook_bullet_4"]))
story.append(bul(ai["outlook_bullet_5"]))
story.append(S(0.1))

# DISCLAIMER
story.append(HRFlowable(width=CW, thickness=0.5, color=MID_GRAY, spaceAfter=0.2*cm))
story.append(Paragraph(
    "<i>DISCLAIMER: Il presente report e' prodotto a esclusivo scopo informativo e non costituisce "
    "consulenza finanziaria, investimento consigliato o sollecitazione all'acquisto/vendita di strumenti "
    "finanziari. Le informazioni contenute si basano su fonti pubblicamente disponibili considerate "
    "affidabili alla data di redazione. NexusGoldOne non si assume alcuna responsabilita' per decisioni "
    "prese sulla base di questo documento. Investire comporta rischi, inclusa la possibile perdita del capitale.</i>",
    ParagraphStyle('disc', fontName='Helvetica-Oblique', fontSize=7,
        textColor=DARK_GRAY, leading=10.5, alignment=TA_CENTER)
))

# BUILD
doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN, topMargin=1.8*cm, bottomMargin=2.2*cm)
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(f"PDF generato: {OUTPUT}")

# ── INVIO TELEGRAM ────────────────────────────────────────────────────────────
BOT_TOKEN      = os.environ.get("BOT_TOKEN")
CHANNEL_ID     = os.environ.get("CHANNEL_ID")
TOPIC_ID       = os.environ.get("TOPIC_ID", "2")
ADMIN_CHAT_ID  = os.environ.get("REVIEW_GROUP_ID", "-5122912249")  # privato admin

def send_admin_alert(token, chat_id, message):
    """Invia un messaggio privato all'admin in caso di errore — mai visibile sul canale."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=15
        )
    except Exception:
        pass  # se anche questo fallisce, logga solo su GitHub Actions

def send_document_with_retry(token, channel_id, topic_id, filepath, filename, caption, retries=3):
    """Invia il PDF con fino a 3 tentativi automatici."""
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with open(filepath, "rb") as f:
                resp = requests.post(url, data={
                    "chat_id":            channel_id,
                    "message_thread_id":  topic_id,
                    "caption":            caption,
                    "parse_mode":         "Markdown",
                }, files={"document": (filename, f, "application/pdf")}, timeout=60)
            result = resp.json()
            if result.get("ok"):
                print(f"PDF inviato con successo (tentativo {attempt}): {filename}")
                return True
            else:
                last_error = f"Telegram API: {result.get('description')} (code {result.get('error_code')})"
                print(f"Tentativo {attempt} fallito: {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f"Tentativo {attempt} — eccezione: {last_error}")
    return last_error  # ritorna il messaggio di errore se tutti i tentativi falliscono

if not BOT_TOKEN or not CHANNEL_ID:
    msg = "⚠️ *NexusGoldOne — Report NON inviato*\nBOT\\_TOKEN o CHANNEL\\_ID mancanti nelle variabili d'ambiente."
    print(msg)
    if BOT_TOKEN:
        send_admin_alert(BOT_TOKEN, ADMIN_CHAT_ID, msg)
else:
    caption = (
        f"📊 *NexusGoldOne — Report Macro & Geopolitica*\n\n"
        f"Analisi settimanale: notizie impattanti, geopolitica globale, banche centrali e price action sull'oro.\n"
        f"{WEEK_LABEL}\n\n"
        f"Buona lettura e buona settimana! ⚡\n\n"
        f"_NexusGoldOne_"
    )
    result = send_document_with_retry(BOT_TOKEN, CHANNEL_ID, TOPIC_ID, OUTPUT, FILENAME, caption)
    if result is not True:
        # Invio fallito — notifica PRIVATA all'admin, nessun messaggio sul canale pubblico
        alert = (
            f"⚠️ *NexusGoldOne — Report NON inviato*\n\n"
            f"Il PDF `{FILENAME}` non è stato consegnato al canale.\n\n"
            f"*Errore:* {result}\n\n"
            f"Vai su GitHub Actions → Run workflow per ritentare manualmente."
        )
        send_admin_alert(BOT_TOKEN, ADMIN_CHAT_ID, alert)
        print(f"Alert privato inviato all'admin. Errore: {result}")
        exit(1)
