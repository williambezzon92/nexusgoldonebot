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
    # Solo notizie delle ultime 36 ore — contesto immediato per la settimana in corso
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)

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

# ── CALENDARIO FOREX FACTORY (eventi USD della settimana) ────────────────────
def get_forex_factory_calendar():
    """
    Scarica il calendario macroeconomico settimanale da Forex Factory (API JSON pubblica).
    Filtra solo eventi USD ad alto e medio impatto.
    Funziona su GitHub Actions — potrebbe essere bloccato in alcuni sandbox locali.
    """
    IMPACT_ORDER = {'High': 0, 'Medium': 1, 'Low': 2, 'Non-Economic': 3, 'Holiday': 4}
    WEEKDAYS_IT = {
        'Monday': 'Lunedì', 'Tuesday': 'Martedì', 'Wednesday': 'Mercoledì',
        'Thursday': 'Giovedì', 'Friday': 'Venerdì',
        'Saturday': 'Sabato', 'Sunday': 'Domenica'
    }
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (NexusGoldOne Report Bot/2.0)',
            'Accept': 'application/json'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Filtra solo eventi USD con impatto High o Medium
        usd_events = []
        for ev in data:
            if ev.get('country', '').upper() != 'USD':
                continue
            impact = ev.get('impact', 'Low')
            if impact not in ('High', 'Medium'):
                continue

            # Parsa la data
            date_str = ev.get('date', '')  # es. "2025-04-21T08:30:00-05:00"
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                day_name_en = dt.strftime('%A')
                day_name_it = WEEKDAYS_IT.get(day_name_en, day_name_en)
                day_label   = f"{day_name_it} {dt.day} {MESI_SHORT[dt.month]}"
                time_label  = dt.strftime('%H:%M') + ' ET'
            except Exception:
                day_label  = date_str[:10]
                time_label = ''

            forecast = ev.get('forecast', '') or '—'
            previous = ev.get('previous', '') or '—'
            title    = ev.get('title', '').strip()

            usd_events.append({
                'title':    title,
                'day':      day_label,
                'time':     time_label,
                'impact':   impact,
                'forecast': forecast,
                'previous': previous,
                'sort_key': date_str,  # datetime ISO reale per ordinamento corretto
            })

        # Ordina per datetime REALE (non per nome del giorno) poi per impatto
        usd_events.sort(key=lambda x: (x['sort_key'], IMPACT_ORDER.get(x['impact'], 9)))
        print(f"Forex Factory: {len(usd_events)} eventi USD High/Medium trovati")

        # Genera nota automatica basata sugli eventi REALI (non sull'AI)
        high_events = [e for e in usd_events if e['impact'] == 'High']
        if high_events:
            top = high_events[0]
            ff_nota = (f"L'evento più importante della settimana è <b>{top['title']}</b> "
                       f"({top['day']}, {top['time']}), classificato ad ALTO impatto. "
                       f"Previsione: {top['forecast']} | Precedente: {top['previous']}. "
                       f"Una lettura fuori dalle attese può generare movimenti significativi su oro e dollaro.")
        else:
            ff_nota = ("Questa settimana non ci sono eventi USD di alto impatto programmati. "
                       "Monitorare comunque i dati a medio impatto che potrebbero sorprendere i mercati.")

        return usd_events, ff_nota

    except Exception as e:
        print(f"Forex Factory non disponibile ({e}) — uso calendario AI")
        return []

print("Recupero calendario Forex Factory (eventi USD)...")
_ff_result = get_forex_factory_calendar()
if isinstance(_ff_result, tuple):
    ff_calendar, ff_nota_reale = _ff_result
else:
    ff_calendar, ff_nota_reale = [], None

# ── NOTIZIE RSS ULTIME 72H (funziona su GitHub Actions) ───────────────────────
print("Recupero notizie RSS ultime 72 ore...")
weekly_news = get_weekly_news()
print(f"Notizie trovate: {len(weekly_news)}")

# ── PROSSIME RIUNIONI FOMC/BCE 2026 ──────────────────────────────────────────
FOMC_2026 = [date(2026,1,28),date(2026,3,17),date(2026,4,28),date(2026,6,9),
             date(2026,7,28),date(2026,9,15),date(2026,10,27),date(2026,12,8)]
ECB_2026  = [date(2026,1,30),date(2026,3,6),date(2026,4,17),date(2026,6,5),
             date(2026,7,24),date(2026,9,11),date(2026,10,23),date(2026,12,11)]
next_fomc = next((d for d in FOMC_2026 if d >= today), None)
next_ecb  = next((d for d in ECB_2026  if d >= today), None)
days_fomc = (next_fomc - today).days if next_fomc else None
days_ecb  = (next_ecb  - today).days if next_ecb  else None
fomc_str  = (f"{next_fomc.day} {MESI[next_fomc.month]} {next_fomc.year} "
             f"(tra {days_fomc} giorni)") if next_fomc else "data TBD"
ecb_str   = (f"{next_ecb.day} {MESI[next_ecb.month]} {next_ecb.year} "
             f"(tra {days_ecb} giorni)") if next_ecb else "data TBD"
print(f"Prossima FOMC: {fomc_str} | Prossima BCE: {ecb_str}")

# ── PREZZI LIVE (Yahoo Finance) ───────────────────────────────────────────────
def get_price(ticker):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        # period="1mo" garantisce >6 righe su GitHub Actions per confronto settimanale affidabile
        hist = t.history(period="1mo")
        if hist.empty or len(hist) < 2:
            return None, None, None, None
        close_last = float(hist["Close"].iloc[-1])
        # Confronto con chiusura di esattamente 5 giorni di trading fa (settimana precedente)
        close_prev = float(hist["Close"].iloc[-6]) if len(hist) >= 6 else float(hist["Close"].iloc[0])
        change_pct = ((close_last - close_prev) / close_prev) * 100
        # Range sugli ultimi 5 giorni di trading
        recent = hist.iloc[-5:]
        week_low  = float(recent["Low"].min())
        week_high = float(recent["High"].max())
        # Sanity check: range > ±15% dal prezzo attuale = dato anomalo yfinance
        if week_high > close_last * 1.15 or week_low < close_last * 0.85:
            week_low, week_high = None, None
        return close_last, change_pct, week_low, week_high
    except Exception as e:
        print(f"Errore prezzo {ticker}: {e}")
        return None, None, None, None

print("Recupero prezzi di mercato...")
xau_price, xau_chg, xau_low, xau_high = get_price("GC=F")
spx_price, spx_chg, spx_low, spx_high = get_price("^GSPC")
ndx_price, ndx_chg, ndx_low, ndx_high = get_price("^IXIC")
dxy_price, dxy_chg, dxy_low, dxy_high = get_price("DX-Y.NYB")
wti_price, wti_chg, wti_low, wti_high = get_price("CL=F")
xag_price, xag_chg, xag_low, xag_high = get_price("SI=F")
# Indicatori aggiuntivi
vix_price, _, _, _                     = get_price("^VIX")      # indice di volatilità/paura
tny_price, _, _, _                     = get_price("^TNX")      # rendimento Treasury 10 anni
eur_price, _, eur_low, eur_high        = get_price("EURUSD=X")  # cambio euro/dollaro

# ── VALIDAZIONE PREZZI AGGIUNTIVI ─────────────────────────────────────────────
# Se i valori sono palesemente impossibili (dati mock), li azzeriamo a None.
# Su GitHub Actions con dati reali questi controlli non scatteranno mai.
if eur_price is not None and not (0.50 < eur_price < 5.00):
    eur_price = None; eur_low = None; eur_high = None
    print("⚠ EUR/USD: valore non realistico ignorato")
if vix_price is not None and not (5.0 < vix_price < 85.0):
    vix_price = None
    print("⚠ VIX: valore non realistico ignorato")
if tny_price is not None and not (0.10 < tny_price < 20.0):
    tny_price = None
    print("⚠ 10Y: valore non realistico ignorato")

def fmt(val, decimals=0, prefix=""):
    if val is None: return "N/D"
    return f"{prefix}{val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_chg(val):
    if val is None: return "N/D"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%".replace(".", ",")

xau_row = ["XAU/USD (Oro)",      f"~${fmt(xau_price, 0)}", f"${fmt(xau_low, 0)} / ${fmt(xau_high, 0)}"]
spx_row = ["S&P 500",            f"~{fmt(spx_price, 0)}",  f"{fmt(spx_low, 0)} / {fmt(spx_high, 0)}"]
ndx_row = ["NASDAQ Composite",   f"~{fmt(ndx_price, 0)}",  f"{fmt(ndx_low, 0)} / {fmt(ndx_high, 0)}"]
dxy_row = ["DXY (Dollaro USA)",  f"~{fmt(dxy_price, 2)}",  f"{fmt(dxy_low, 2)} / {fmt(dxy_high, 2)}"]
# Indicatori aggiuntivi (tabella separata nel PDF)
vix_label = ("Bassa" if vix_price and vix_price<15 else
             "Moderata" if vix_price and vix_price<25 else
             "Alta" if vix_price and vix_price<35 else "Estrema") if vix_price else "—"
eur_row = ["EUR/USD",            f"~{fmt(eur_price, 4)}",  f"{fmt(eur_low,4)} / {fmt(eur_high,4)}"]
vix_row = ["VIX (Volatilità)",   f"~{fmt(vix_price, 1)}",  vix_label]
tny_row = ["Rendimento 10Y USA", f"~{fmt(tny_price, 2)}%", "—"]

# ── ANALISI AI DINAMICA (Claude Haiku) ───────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ai = None

if ANTHROPIC_API_KEY:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Prepara lista notizie RSS per arricchire il contesto AI
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

DATI DI MERCATO REALI (aggiornati a oggi — lunedì mattina):
- XAU/USD (Oro): ${fmt(xau_price, 0)} | Range settimana: ${fmt(xau_low,0)}-${fmt(xau_high,0)}
- S&P 500: {fmt(spx_price, 0)} | Range: {fmt(spx_low,0)}-{fmt(spx_high,0)}
- NASDAQ: {fmt(ndx_price, 0)} | Range: {fmt(ndx_low,0)}-{fmt(ndx_high,0)}
- DXY: {fmt(dxy_price, 2)} | Range: {fmt(dxy_low,2)}-{fmt(dxy_high,2)}
- WTI Crude Oil: ${fmt(wti_price, 1)} | Range: ${fmt(wti_low,1)}-${fmt(wti_high,1)}
- XAG/USD (Argento): ${fmt(xag_price, 2)}
- EUR/USD: {fmt(eur_price, 4)}
- VIX (volatilità/paura): {fmt(vix_price, 1)} ({vix_label})
- Rendimento Treasury 10Y USA: {fmt(tny_price, 2)}%
- Prossima FOMC: {fomc_str}
- Prossima BCE: {ecb_str}
{news_text}

Settimana corrente: Lun {lun.day} {MESI_SHORT[lun.month]}, Mar {mar.day}, Mer {mer.day}, Gio {gio.day}, Ven {ven.day} {MESI_SHORT[ven.month]} {ven.year}

Genera un'analisi macro-geopolitica AGGIORNATA e SPECIFICA per {today.strftime('%B %Y')}.
Basa l'analisi sulle notizie reali ricevute. Tono professionale per investitori retail sull'oro.
Tutto in italiano. Nei testi usa tag HTML <b>Titolo:</b> per i bullet. Niente markdown.

Rispondi SOLO con JSON valido, nessun testo fuori:
{{
  "snapshot_commento": "2-3 frasi tecniche sui prezzi reali di questa settimana, citando i valori esatti",
  "geopolitica_intro": "3-4 frasi sulla situazione geopolitica ATTUALE di {today.strftime('%B %Y')}, basata sulle notizie reali",
  "geo_bullet_1": "<b>Medio Oriente / Iran–USA:</b> situazione aggiornata con dettagli specifici e impatto su XAU/USD",
  "geo_bullet_2": "<b>Russia–Ucraina:</b> sviluppi della settimana, posizione NATO, impatto safe haven",
  "geo_bullet_3": "<b>Cina–Taiwan–USA:</b> tensioni commerciali e militari, terre rare, semiconduttori",
  "geo_bullet_4": "<b>De-dollarizzazione / BRICS+:</b> acquisti banche centrali, accordi valutari alternativi",
  "geo_bullet_5": "<b>Energia / Petrolio:</b> stato OPEC+, Stretto di Hormuz, impatto WTI sull'oro",
  "geo_bullet_6": "<b>Dazi USA e guerra commerciale:</b> misure in vigore, ritorsioni, impatto inflazione e oro",
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
  "outlook_bullet_5": "<b>Scenario base:</b> visione complessiva e bias direzionale per la settimana",
  "wti_intro": "2 frasi su WTI Crude Oil nel contesto attuale: prezzo, driver, correlazione con oro",
  "wti_bullet_1": "<b>Prezzo WTI:</b> livello attuale, variazione settimanale, range e driver principali",
  "wti_bullet_2": "<b>OPEC+ e offerta:</b> decisioni recenti o attese OPEC+, impatto su supply globale",
  "wti_bullet_3": "<b>Correlazione oro–petrolio:</b> come il movimento del WTI si riflette su XAU/USD questa settimana",
  "silver_bullet_1": "<b>XAG/USD (Argento):</b> prezzo attuale, ratio oro/argento, trend tecnico",
  "silver_bullet_2": "<b>Domanda industriale argento:</b> settori chiave (solare, EV, semiconduttori) e impatto sul prezzo"
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
        "snapshot_commento": f"L'oro (XAU/USD) chiude la settimana a ${fmt(xau_price, 0)}, mantenendo la sua traiettoria strutturalmente rialzista. S&amp;P 500 a {fmt(spx_price, 0)} e DXY a {fmt(dxy_price, 2)} completano il quadro macro settimanale.",
        "geopolitica_intro": "Il quadro geopolitico internazionale continua a sostenere la domanda di beni rifugio. Le tensioni in Medio Oriente, le manovre nello Stretto di Taiwan e la guerra commerciale USA-Cina mantengono elevata l'incertezza strutturale sui mercati globali.",
        "geo_bullet_1": "<b>Medio Oriente:</b> situazione in evoluzione. Monitorare sviluppi su infrastrutture energetiche e approvvigionamento petrolifero globale.",
        "geo_bullet_2": "<b>USA-Cina:</b> tensioni commerciali e militari nello Stretto di Taiwan. Impatto sulle catene di fornitura dei semiconduttori.",
        "geo_bullet_3": "<b>Guerra commerciale:</b> dazi USA mantengono pressione sull'inflazione globale e incertezza normativa.",
        "geo_bullet_4": "<b>De-dollarizzazione:</b> BRICS+ accelera la diversificazione dalle riserve in dollari verso l'oro fisico.",
        "geo_bullet_5": f"<b>Energia / Petrolio:</b> WTI a ${fmt(wti_price,0)}. OPEC+ mantiene i tagli alla produzione. La volatilita' del WTI supporta la domanda di beni rifugio.",
        "geo_bullet_6": "<b>Dazi USA:</b> le misure tariffarie mantengono pressione inflazionistica e incertezza normativa sui mercati globali.",
        "azionario_intro": "I mercati azionari USA navigano in un contesto di dati macro contrastanti. La stagione degli utili e le aspettative Fed rimangono i principali driver di breve termine.",
        "sp500_bullet_1": f"<b>Livelli chiave:</b> S&amp;P 500 a {spx_row[1]}. Supporto in area {fmt(spx_low, 0)}, resistenza in area {fmt(spx_high, 0)}.",
        "sp500_bullet_2": "<b>Rischi principali:</b> dazi su farmaci e manifatturiero comprimono i margini aziendali. Volatilita' settoriale elevata.",
        "sp500_bullet_3": "<b>Opportunita':</b> dati macro positivi e utili sopra attese potrebbero supportare i livelli attuali.",
        "ndx_bullet_1": f"<b>NASDAQ:</b> {ndx_row[1]}. Il settore tech reagisce a tensioni commerciali e dazi su semiconduttori.",
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
        "fed_bullet_1": "<b>Tassi Fed:</b> range attuale 4,25%–4,50%. Politica monetaria restrittiva in attesa di dati CPI/PCE più favorevoli.",
        "fed_bullet_2": f"<b>Prossima FOMC:</b> {fomc_str}. Mercati prezzano 2–3 tagli totali nel {today.year}. Il timing dipende da inflazione e occupazione.",
        "fed_bullet_3": "<b>Attenzione:</b> dati CPI e PCE determinanti per il percorso dei tassi.",
        "fed_bullet_4": "<b>Nota:</b> dichiarazioni dei membri Fed da monitorare per forward guidance.",
        "bce_bullet_1": "<b>Tassi BCE:</b> Tasso deposito al 2,25%. Ciclo di allentamento monetario in corso in Europa dopo la serie di tagli dal 2024.",
        "bce_bullet_2": f"<b>Prossima riunione BCE:</b> {ecb_str}. Atteso ulteriore taglio 25 bps se inflazione Eurozona continua a moderarsi verso il target 2%.",
        "cal_lun_evento": "Apertura mercati / aggiornamento geopolitica", "cal_lun_mercati": "Oro, Indici", "cal_lun_imp": "🟠 Alta",
        "cal_mar_evento": "Dati manifatturiero / dichiarazioni Fed", "cal_mar_mercati": "Dollaro, Oro", "cal_mar_imp": "🟠 Alta",
        "cal_mer_evento": "CPI USA / Scorte petrolio EIA", "cal_mer_mercati": "Fed, Dollaro, Oro", "cal_mer_imp": "🔴 Critica",
        "cal_gio_evento": "PPI USA / Sussidi disoccupazione settimanali", "cal_gio_mercati": "Dollaro, Oro", "cal_gio_imp": "🟠 Alta",
        "cal_ven_evento": "Sentiment consumatori / Dichiarazioni BCE", "cal_ven_mercati": "Euro, S&amp;P 500, Oro", "cal_ven_imp": "🟡 Media",
        "cal_nota": "Il dato CPI del mercoledi' e' tipicamente il piu' atteso della settimana. Una lettura sopra le attese aumenta la probabilita' di un rinvio dei tagli Fed.",
        "outlook_intro": "Il quadro macro-geopolitico rimane strutturalmente favorevole all'oro nel medio termine. La domanda delle banche centrali e le tensioni geopolitiche costituiscono un floor robusto per XAU/USD.",
        "outlook_bullet_1": f"<b>XAU/USD:</b> ${fmt(xau_price,0)} — supporto in area ${fmt(xau_low, 0)}, resistenza in area ${fmt(xau_high, 0)}. Bias rialzista strutturale confermato.",
        "outlook_bullet_2": f"<b>S&amp;P 500:</b> {fmt(spx_price,0)} — area {fmt(spx_low, 0)} come supporto chiave della settimana.",
        "outlook_bullet_3": "<b>Dati macro USA:</b> CPI e PPI determinanti per le aspettative Fed. Lettura sopra attese = opportunita' di acquisto nel medio termine.",
        "outlook_bullet_4": f"<b>Target analisti oro {today.year}:</b> Goldman Sachs $5.000, UBS $4.500, JP Morgan $4.800. Consensus rivisto al rialzo dopo il rally sopra $4.000. Bull case $5.500+ se ciclo tagli Fed accelera.",
        "outlook_bullet_5": "<b>Scenario base:</b> consolidamento sopra i supporti con possibili spike di volatilita'. Bias strutturale rialzista confermato.",
        "wti_intro": f"Il WTI Crude Oil quota ${fmt(wti_price,0)} questa settimana. Dinamiche OPEC+ e tensioni geopolitiche guidano la volatilita'. La correlazione con l'oro rimane un indicatore chiave per i trader.",
        "wti_bullet_1": f"<b>Prezzo WTI:</b> ${fmt(wti_price,0)}. Range settimana: ${fmt(wti_low,0)}–${fmt(wti_high,0)}. Volatilita' elevata per tensioni Medio Oriente.",
        "wti_bullet_2": f"<b>OPEC+ e offerta:</b> i tagli alla produzione rimangono in vigore. Prossima riunione da monitorare per segnali di inversione su supply {today.year}.",
        "wti_bullet_3": "<b>Correlazione oro–petrolio:</b> un WTI in rialzo per ragioni geopolitiche tende a supportare XAU/USD come asset rifugio.",
        "silver_bullet_1": f"<b>XAG/USD (Argento):</b> ${fmt(xag_price,1)}. Ratio oro/argento: {round(xau_price/xag_price) if xau_price and xag_price else 'N/D'}:1 — argento storicamente conveniente rispetto all'oro.",
        "silver_bullet_2": "<b>Domanda industriale argento:</b> i settori solare ed EV mantengono forte domanda strutturale. Supporto al prezzo nel medio termine.",
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

def ff_calendar_tbl(events):
    """Genera la tabella del calendario Forex Factory con eventi USD della settimana."""
    if not events:
        return None  # Usa il calendario AI come fallback

    hdr_style = ParagraphStyle('ff_hdr', fontName='Helvetica-Bold', fontSize=8.5,
                    textColor=colors.white, alignment=TA_CENTER, leading=12)
    cell_style = ParagraphStyle('ff_cell', fontName='Helvetica', fontSize=8.5,
                    textColor=TEXT_COLOR, leading=12, wordWrap='LTR')
    day_style  = ParagraphStyle('ff_day', fontName='Helvetica-Bold', fontSize=8.5,
                    textColor=TEXT_COLOR, alignment=TA_CENTER, leading=12)
    time_style = ParagraphStyle('ff_time', fontName='Helvetica', fontSize=8,
                    textColor=DARK_GRAY, alignment=TA_CENTER, leading=12)

    rows = [[
        Paragraph('Giorno', hdr_style),
        Paragraph('Orario (ET)', hdr_style),
        Paragraph('Evento Macroeconomico USD', hdr_style),
        Paragraph('Impatto', hdr_style),
        Paragraph('Prev. / Prec.', hdr_style),
    ]]
    row_bgs = []

    for i, ev in enumerate(events[:18]):  # max 18 righe
        if ev['impact'] == 'High':
            ic, imp_text = RED_IMPACT, 'ALTO'
        else:
            ic, imp_text = ORG_IMPACT, 'MEDIO'

        imp_style = ParagraphStyle(f'ff_imp_{i}', fontName='Helvetica-Bold', fontSize=8.5,
                        textColor=ic, alignment=TA_CENTER, leading=12)
        fp = f"{ev['forecast']} / {ev['previous']}"
        rows.append([
            Paragraph(ev['day'],    day_style),
            Paragraph(ev['time'],   time_style),
            Paragraph(ev['title'],  cell_style),
            Paragraph(imp_text,     imp_style),
            Paragraph(fp,           time_style),
        ])
        row_bgs.append(LIGHT_GRAY if i % 2 == 1 else colors.white)

    t = Table(rows, colWidths=[CW*0.18, CW*0.12, CW*0.38, CW*0.12, CW*0.20])
    style = [
        ('BACKGROUND',    (0,0), (-1,0), DARK_NAVY),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('GRID',          (0,0), (-1,-1), 0.4, MID_GRAY),
        ('BOX',           (0,0), (-1,-1), 0.5, colors.HexColor('#BDC3C7')),
    ]
    for i, bg in enumerate(row_bgs):
        style.append(('BACKGROUND', (0, i+1), (-1, i+1), bg))
    t.setStyle(TableStyle(style))
    return t

def news_tbl(articles):
    if not articles:
        return body("Nessuna notizia di alto impatto rilevata nelle ultime 36 ore. Fare riferimento al calendario eventi della settimana (Sezione 8) per gli appuntamenti macro in agenda.")

    # Stili con leading aumentato per evitare sovrapposizioni
    hdr_style  = ParagraphStyle('ntbl_hdr', fontName='Helvetica-Bold', fontSize=8.5,
                     textColor=colors.white, alignment=TA_CENTER, leading=13)
    date_style = ParagraphStyle('ntbl_date', fontName='Helvetica', fontSize=8,
                     textColor=TEXT_COLOR, alignment=TA_CENTER, leading=13)
    cell_style = ParagraphStyle('ntbl_cell', fontName='Helvetica', fontSize=8.5,
                     textColor=TEXT_COLOR, leading=13, wordWrap='LTR')
    src_style  = ParagraphStyle('ntbl_src', fontName='Helvetica-Oblique', fontSize=8,
                     textColor=DARK_GRAY, leading=13, wordWrap='LTR')

    rows = [[
        Paragraph('Imp.', hdr_style),
        Paragraph('Data', hdr_style),
        Paragraph('Titolo (EN)', hdr_style),
        Paragraph('Fonte', hdr_style),
    ]]

    row_bgs = []

    for i, art in enumerate(articles):
        if '🔴' in art['impact'] or 'CRITICO' in art['impact'].upper():
            ic       = RED_IMPACT
            imp_text = 'CRITICO'
        elif '🟠' in art['impact'] or 'ALTO' in art['impact'].upper():
            ic       = ORG_IMPACT
            imp_text = 'ALTO'
        else:
            ic       = YEL_IMPACT
            imp_text = 'MEDIO'

        imp_style = ParagraphStyle(f'ntbl_imp_{i}', fontName='Helvetica-Bold', fontSize=8.5,
                        textColor=ic, alignment=TA_CENTER, leading=13)

        # Titolo troncato a 80 chars per evitare overflow celle
        title_text = art['title'][:80] + ('...' if len(art['title']) > 80 else '')
        # Fonte: abbrevia nomi lunghi
        src_text = art['source'].replace('Gold News', 'Gold').replace('Finance', 'Fin.').replace('Markets', 'Mkt')

        rows.append([
            Paragraph(imp_text, imp_style),
            Paragraph(art['date_str'], date_style),
            Paragraph(title_text, cell_style),
            Paragraph(src_text, src_style),
        ])

        row_bgs.append(LIGHT_GRAY if i % 2 == 1 else colors.white)

    # Colonne: imp=13%, data=9%, titolo=52%, fonte=26%
    t = Table(rows, colWidths=[CW*0.13, CW*0.09, CW*0.52, CW*0.26])
    style = [
        ('BACKGROUND',    (0,0), (-1,0), DARK_NAVY),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 7),
        ('RIGHTPADDING',  (0,0), (-1,-1), 7),
        ('GRID',          (0,0), (-1,-1), 0.4, MID_GRAY),
        ('BOX',           (0,0), (-1,-1), 0.5, colors.HexColor('#BDC3C7')),
        ('WORDWRAP',      (0,0), (-1,-1), 'LTR'),
    ]
    for i, bg in enumerate(row_bgs):
        style.append(('BACKGROUND', (0, i+1), (-1, i+1), bg))
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
    ['Asset', 'Prezzo Attuale', 'Min / Max Settimana'],
    xau_row, spx_row, ndx_row, dxy_row,
]
story.append(tbl(price_data, [CW*0.38, CW*0.28, CW*0.34]))
if eur_price is not None or vix_price is not None or tny_price is not None:
    story.append(S(0.08))
    story.append(sub("Indicatori Chiave"))
    indic_data = [
        ['Indicatore', 'Valore Attuale', 'Contesto'],
        eur_row, vix_row, tny_row,
    ]
    story.append(tbl(indic_data, [CW*0.38, CW*0.28, CW*0.34]))
story.append(S(0.1))
story.append(body(ai["snapshot_commento"]))

# SEZ 2 — AGENDA MACROECONOMICA USD (Forex Factory o AI fallback — sempre forward-looking)
story.extend(sec(f"2. Agenda Macroeconomica USD — {WEEK_LABEL}"))
_ff_tbl = ff_calendar_tbl(ff_calendar)
if _ff_tbl is not None:
    story.append(body(
        f"Dati reali da <b>Forex Factory</b> — tutti gli eventi USD ad alto e medio impatto "
        f"per la settimana {WEEK_SHORT}. "
        f"Gli eventi ad alto impatto possono muovere oro, dollaro e indici di punti percentuali in poche ore. "
        f"Orari in ET (Eastern Time, UTC-4)."
    ))
    story.append(S(0.08))
    story.append(_ff_tbl)
else:
    story.append(body(
        f"Principali eventi macroeconomici USD attesi questa settimana ({WEEK_SHORT}). "
        f"Gli appuntamenti ad alta importanza possono generare movimenti significativi su oro, dollaro e indici."
    ))
    story.append(S(0.08))
    # Calendario AI fallback
    _cal_hdr  = ParagraphStyle('cal_hdr2', fontName='Helvetica-Bold', fontSize=9,
                    textColor=colors.white, alignment=TA_CENTER, leading=12)
    _cal_date = ParagraphStyle('cal_date2', fontName='Helvetica-Bold', fontSize=9,
                    textColor=TEXT_COLOR, alignment=TA_CENTER, leading=12)
    _cal_cell = ParagraphStyle('cal_cell2', fontName='Helvetica', fontSize=9,
                    textColor=TEXT_COLOR, leading=12)
    def _il(text):
        t=text.upper()
        if 'CRITICA' in t or 'CRITICO' in t: return 'CRITICA',RED_IMPACT
        if 'ALTA' in t or 'ALTO' in t: return 'ALTA',ORG_IMPACT
        return 'MEDIA',YEL_IMPACT
    def _ip(label,col,idx):
        s=ParagraphStyle(f'cal_imp2_{idx}',fontName='Helvetica-Bold',fontSize=9,
                textColor=col,alignment=TA_CENTER,leading=12)
        return Paragraph(label,s)
    _GIORNI_SHORT = {0:'Lun',1:'Mar',2:'Mer',3:'Gio',4:'Ven',5:'Sab',6:'Dom'}
    def _gf(d): return f"{_GIORNI_SHORT[d.weekday()]} {d.day} {MESI_SHORT[d.month]}"
    _lun=monday;_mar=monday+timedelta(1);_mer=monday+timedelta(2)
    _gio=monday+timedelta(3);_ven=monday+timedelta(4)
    _li,_lc=_il(ai["cal_lun_imp"]);_mi,_mc=_il(ai["cal_mar_imp"])
    _mei,_mec=_il(ai["cal_mer_imp"]);_gi,_gc=_il(ai["cal_gio_imp"]);_vi,_vc=_il(ai["cal_ven_imp"])
    _cal_data=[
        [Paragraph('Data',_cal_hdr),Paragraph('Evento',_cal_hdr),
         Paragraph('Mercati',_cal_hdr),Paragraph('Importanza',_cal_hdr)],
        [Paragraph(_gf(_lun),_cal_date),Paragraph(ai["cal_lun_evento"],_cal_cell),
         Paragraph(ai["cal_lun_mercati"],_cal_cell),_ip(_li,_lc,0)],
        [Paragraph(_gf(_mar),_cal_date),Paragraph(ai["cal_mar_evento"],_cal_cell),
         Paragraph(ai["cal_mar_mercati"],_cal_cell),_ip(_mi,_mc,1)],
        [Paragraph(_gf(_mer),_cal_date),Paragraph(ai["cal_mer_evento"],_cal_cell),
         Paragraph(ai["cal_mer_mercati"],_cal_cell),_ip(_mei,_mec,2)],
        [Paragraph(_gf(_gio),_cal_date),Paragraph(ai["cal_gio_evento"],_cal_cell),
         Paragraph(ai["cal_gio_mercati"],_cal_cell),_ip(_gi,_gc,3)],
        [Paragraph(_gf(_ven),_cal_date),Paragraph(ai["cal_ven_evento"],_cal_cell),
         Paragraph(ai["cal_ven_mercati"],_cal_cell),_ip(_vi,_vc,4)],
    ]
    _cal_t=Table(_cal_data,colWidths=[CW*0.16,CW*0.38,CW*0.25,CW*0.21])
    _cal_t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),DARK_NAVY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT_GRAY]),
        ('GRID',(0,0),(-1,-1),0.5,MID_GRAY),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#BDC3C7')),
    ]))
    story.append(_cal_t)
story.append(S(0.1))
# Nota: usa i dati REALI di FF se disponibili, altrimenti quella dell'AI
_nota_finale = ff_nota_reale if ff_nota_reale else ai['cal_nota']
story.append(body(f"<b>Nota:</b> {_nota_finale}"))
story.append(PageBreak())

# SEZ 2b — NOTIZIE FLASH ULTIME 72 ORE (solo se ci sono notizie)
if weekly_news:
    story.extend(sec("2b. Notizie Flash — Ultime 72 Ore"))
    story.append(body(
        f"Notizie di alto impatto dai principali feed finanziari globali, aggiornate al {today.strftime('%d %B %Y')}. "
        f"Fonti: Kitco Gold News, Reuters, Yahoo Finance, CNBC, MarketWatch. "
        f"Le notizie sono classificate per rilevanza (Critico / Alto / Medio) in base all'impatto atteso su oro, dollaro e mercati."
    ))
    story.append(S(0.08))
    story.append(news_tbl(weekly_news))
    story.append(S(0.1))

# SEZ 3 — GEOPOLITICA
story.extend(sec("3. Geopolitica — Scenario Globale"))
story.append(body(ai["geopolitica_intro"]))
story.append(bul(ai["geo_bullet_1"]))
story.append(bul(ai["geo_bullet_2"]))
story.append(bul(ai["geo_bullet_3"]))
story.append(bul(ai["geo_bullet_4"]))
story.append(bul(ai.get("geo_bullet_5", "")))
story.append(bul(ai.get("geo_bullet_6", "")))

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
# CondPageBreak invece di PageBreak — nuova pagina solo se rimangono < 6cm
story.append(CondPageBreak(6*cm))

# SEZ 4b — COMMODITIES (WTI + Argento)
story.extend(sec("4b. Commodity — WTI Crude Oil e Argento"))
story.append(body(ai.get("wti_intro", "Il petrolio e l'argento sono asset chiave da monitorare in correlazione con l'oro.")))
story.append(sub("WTI Crude Oil"))
story.append(bul(ai.get("wti_bullet_1", "")))
story.append(bul(ai.get("wti_bullet_2", "")))
story.append(bul(ai.get("wti_bullet_3", "")))
story.append(sub("Argento (XAG/USD)"))
story.append(bul(ai.get("silver_bullet_1", "")))
story.append(bul(ai.get("silver_bullet_2", "")))
story.append(S(0.1))

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
story.append(CondPageBreak(5*cm))

# SEZ 8 — OUTLOOK
story.extend(sec(f"8. Outlook — {WEEK_LABEL}"))
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
