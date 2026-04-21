#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NexusGoldOne — Generatore automatico Report Macro & Geopolitica
Gira ogni lunedì su GitHub Actions e invia il PDF al canale Telegram.
Versione 3.0 — Struttura completa:
  1. Snapshot Prezzi (+ Indicatori Chiave: EUR/USD, VIX, 10Y)
  2. Agenda Macroeconomica USD (Forex Factory o AI fallback)
  2b. Notizie Flash RSS (ultime 72 ore)
  3. Geopolitica
  4. Mercati Azionari (S&P + NASDAQ)
  4b. Commodity (WTI + Argento)
  5. De-Dollarizzazione
  6. Dazi USA
  7. Banche Centrali (Fed + BCE)
  8. Outlook settimanale
"""

import os
import json
import re
import requests
from datetime import date, datetime, timedelta, timezone

# ── DATE AUTOMATICHE ──────────────────────────────────────────────────────────
today  = date.today()
monday = today - timedelta(days=today.weekday())
friday = monday + timedelta(days=4)
lun = monday
mar = monday + timedelta(1)
mer = monday + timedelta(2)
gio = monday + timedelta(3)
ven = monday + timedelta(4)

MESI = {
    1:"Gennaio", 2:"Febbraio", 3:"Marzo", 4:"Aprile",
    5:"Maggio", 6:"Giugno", 7:"Luglio", 8:"Agosto",
    9:"Settembre", 10:"Ottobre", 11:"Novembre", 12:"Dicembre"
}
MESI_SHORT = {
    1:"Gen", 2:"Feb", 3:"Mar", 4:"Apr", 5:"Mag", 6:"Giu",
    7:"Lug", 8:"Ago", 9:"Set", 10:"Ott", 11:"Nov", 12:"Dic"
}
WEEKDAYS_IT = {
    'Monday':'Lunedì','Tuesday':'Martedì','Wednesday':'Mercoledì',
    'Thursday':'Giovedì','Friday':'Venerdì','Saturday':'Sabato','Sunday':'Domenica'
}

WEEK_LABEL = f"Settimana dal {monday.day:02d} al {friday.day:02d} {MESI[friday.month]} {friday.year}"
WEEK_SHORT = f"{monday.day:02d} {MESI_SHORT[monday.month]} – {friday.day:02d} {MESI_SHORT[friday.month]} {friday.year}"
FILENAME   = f"MACRO_Geopolitica_{monday.strftime('%d-%m-%Y')}.pdf"
OUTPUT     = f"/tmp/{FILENAME}"

print(f"=== NexusGoldOne Report Generator v3.0 ===")
print(f"Data: {today.strftime('%d/%m/%Y')} | Settimana: {WEEK_SHORT}")

# ── PREZZI REALI DA YFINANCE ──────────────────────────────────────────────────
def get_price(ticker):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        # period="1mo" garantisce >6 righe su GitHub Actions per confronto settimanale affidabile
        hist = t.history(period="1mo")
        if hist.empty or len(hist) < 2:
            return None, None, None, None
        cl = float(hist["Close"].iloc[-1])
        # Confronto con chiusura di esattamente 5 giorni di trading fa (settimana precedente)
        cp = float(hist["Close"].iloc[-6]) if len(hist) >= 6 else float(hist["Close"].iloc[0])
        chg = ((cl - cp) / cp) * 100
        # Range sugli ultimi 5 giorni di trading
        recent = hist.iloc[-5:]
        wl = float(recent["Low"].min())
        wh = float(recent["High"].max())
        # Sanity check: range > ±15% dal prezzo attuale = dato anomalo yfinance
        if wh > cl * 1.15 or wl < cl * 0.85:
            wl, wh = None, None
        return cl, chg, wl, wh
    except Exception as e:
        print(f"  Errore {ticker}: {e}")
        return None, None, None, None

print("\n[1/4] Recupero prezzi di mercato...")
xau_price, xau_chg, xau_low, xau_high = get_price("GC=F")
spx_price, spx_chg, spx_low, spx_high = get_price("^GSPC")
ndx_price, ndx_chg, ndx_low, ndx_high = get_price("^IXIC")
dxy_price, dxy_chg, dxy_low, dxy_high = get_price("DX-Y.NYB")
wti_price, wti_chg, wti_low, wti_high = get_price("CL=F")
xag_price, xag_chg, xag_low, xag_high = get_price("SI=F")
# Indicatori aggiuntivi
vix_price, _, _, _               = get_price("^VIX")
tny_price, _, _, _               = get_price("^TNX")
eur_price, _, eur_low, eur_high  = get_price("EURUSD=X")

# ── VALIDAZIONE PREZZI AGGIUNTIVI ─────────────────────────────────────────────
# Se i valori sono palesemente impossibili (dati mock sandbox), li azzeriamo a None.
# Su GitHub Actions con dati reali questi controlli non scatteranno mai.
if eur_price is not None and not (0.50 < eur_price < 5.00):
    eur_price = None; eur_low = None; eur_high = None
    print("  ⚠ EUR/USD: valore non realistico ignorato (dati mock sandbox)")
if vix_price is not None and not (5.0 < vix_price < 85.0):
    vix_price = None
    print("  ⚠ VIX: valore non realistico ignorato (dati mock sandbox)")
if tny_price is not None and not (0.10 < tny_price < 20.0):
    tny_price = None
    print("  ⚠ 10Y: valore non realistico ignorato (dati mock sandbox)")

if xau_price: print(f"  ✓ ORO: ${xau_price:,.0f}")
if vix_price: print(f"  ✓ VIX: {vix_price:.1f}")
if eur_price: print(f"  ✓ EUR/USD: {eur_price:.4f}")
if tny_price: print(f"  ✓ 10Y: {tny_price:.2f}%")

def fmt(v, d=0, p=""): return "N/D" if v is None else f"{p}{v:,.{d}f}".replace(",","X").replace(".",",").replace("X",".")
def fmt_chg(v): return "N/D" if v is None else f"{'+' if v>=0 else ''}{v:.1f}%".replace(".",",")

# ── PROSSIME RIUNIONI FOMC/BCE 2026 ──────────────────────────────────────────
FOMC_2026 = [date(2026,1,28), date(2026,3,17), date(2026,4,28), date(2026,6,9),
             date(2026,7,28), date(2026,9,15), date(2026,10,27), date(2026,12,8)]
ECB_2026  = [date(2026,1,30), date(2026,3,6),  date(2026,4,17), date(2026,6,5),
             date(2026,7,24), date(2026,9,11),  date(2026,10,23), date(2026,12,11)]
next_fomc = next((d for d in FOMC_2026 if d >= today), None)
next_ecb  = next((d for d in ECB_2026  if d >= today), None)
days_fomc = (next_fomc - today).days if next_fomc else None
days_ecb  = (next_ecb  - today).days if next_ecb  else None
fomc_str  = (f"{next_fomc.day} {MESI[next_fomc.month]} {next_fomc.year} "
             f"(tra {days_fomc} giorni)") if next_fomc else "data TBD"
ecb_str   = (f"{next_ecb.day} {MESI[next_ecb.month]} {next_ecb.year} "
             f"(tra {days_ecb} giorni)") if next_ecb else "data TBD"
print(f"  Prossima FOMC: {fomc_str} | Prossima BCE: {ecb_str}")

xau_row = ["XAU/USD (Oro)",     f"~${fmt(xau_price,0)}",  f"${fmt(xau_low,0)} / ${fmt(xau_high,0)}"]
spx_row = ["S&P 500",           f"~{fmt(spx_price,0)}",   f"{fmt(spx_low,0)} / {fmt(spx_high,0)}"]
ndx_row = ["NASDAQ Composite",  f"~{fmt(ndx_price,0)}",   f"{fmt(ndx_low,0)} / {fmt(ndx_high,0)}"]
dxy_row = ["DXY (Dollaro USA)", f"~{fmt(dxy_price,2)}",   f"{fmt(dxy_low,2)} / {fmt(dxy_high,2)}"]

# Indicatori secondari
vix_label = ("Bassa" if vix_price and vix_price < 15 else
             "Moderata" if vix_price and vix_price < 25 else
             "Alta" if vix_price and vix_price < 35 else "Estrema") if vix_price else "—"
eur_row = ["EUR/USD",             f"~{fmt(eur_price,4)}",  f"{fmt(eur_low,4)} / {fmt(eur_high,4)}"]
vix_row = ["VIX (Volatilità)",    f"~{fmt(vix_price,1)}",  vix_label]
tny_row = ["Rendimento 10Y USA",  f"~{fmt(tny_price,2)}%", "—"]

# ── FOREX FACTORY CALENDAR ────────────────────────────────────────────────────
def get_ff_calendar():
    """Tenta di scaricare il calendario reale da Forex Factory. Funziona su GitHub Actions."""
    IMPACT_ORDER = {'High': 0, 'Medium': 1}
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        resp = requests.get(url, headers={
            'User-Agent': 'NexusGoldOne/2.0', 'Accept': 'application/json'
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        events = []
        for ev in data:
            if ev.get('country', '').upper() != 'USD': continue
            impact = ev.get('impact', 'Low')
            if impact not in ('High', 'Medium'): continue
            date_str = ev.get('date', '')
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                day_it    = WEEKDAYS_IT.get(dt.strftime('%A'), dt.strftime('%A'))
                day_label = f"{day_it} {dt.day} {MESI_SHORT[dt.month]}"
                time_label = dt.strftime('%H:%M') + ' ET'
                sort_key  = dt.isoformat()
            except Exception:
                day_label = date_str[:10]; time_label = ''; sort_key = date_str
            events.append({
                'title':    ev.get('title', '').strip(),
                'day':      day_label,
                'time':     time_label,
                'impact':   impact,
                'forecast': ev.get('forecast', '') or '—',
                'previous': ev.get('previous', '') or '—',
                'sort_key': sort_key,
            })
        events.sort(key=lambda x: (x['sort_key'], IMPACT_ORDER.get(x['impact'], 9)))
        high_evs = [e for e in events if e['impact'] == 'High']
        if high_evs:
            top = high_evs[0]
            ff_nota = (f"L'evento più importante della settimana è <b>{top['title']}</b> "
                       f"({top['day']}, {top['time']}), classificato ad ALTO impatto. "
                       f"Previsione: {top['forecast']} | Precedente: {top['previous']}.")
        else:
            ff_nota = "Nessun evento USD di alto impatto programmato questa settimana. Monitorare i dati a medio impatto."
        print(f"  ✓ Forex Factory: {len(events)} eventi USD trovati")
        return events, True, ff_nota
    except Exception as e:
        print(f"  Forex Factory non raggiungibile ({e}) — uso calendario AI")
        return [], False, None

# ── NOTIZIE AUTOMATICHE DA RSS FEEDS ─────────────────────────────────────────
def get_weekly_news():
    try:
        import feedparser
    except ImportError:
        print("  feedparser non installato, saltando notizie.")
        return []
    feeds = [
        ("Kitco Gold News",    "https://www.kitco.com/rss/kitconews.rss"),
        ("Reuters Markets",    "https://feeds.reuters.com/reuters/businessNews"),
        ("Yahoo Finance",      "https://finance.yahoo.com/rss/topstories"),
        ("MarketWatch",        "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines"),
        ("CNBC Finance",       "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ]
    KEYWORDS_HIGH = [
        'gold', 'xau', 'federal reserve', 'fed rate', 'inflation', 'cpi', 'pce',
        'war', 'attack', 'strike', 'conflict', 'crisis', 'nuclear',
        'china', 'russia', 'iran', 'middle east', 'ukraine', 'taiwan',
        'central bank', 'brics', 'de-dollarization', 'dollar', 'dxy',
        'sanctions', 'tariff', 'trade war', 'recession', 'oil price',
        'powell', 'opec', 'ceasefire', 'geopolitical', 'interest rate', 'rate cut',
    ]
    KEYWORDS_MED = [
        'market', 'stocks', 'sp500', 'nasdaq', 'euro', 'treasury',
        'jobs', 'unemployment', 'gdp', 'economy', 'silver', 'commodity',
    ]
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
    for source_name, url in feeds:
        try:
            feed = feedparser.parse(url, request_headers={
                'User-Agent': 'Mozilla/5.0 (NexusGoldOne Report Bot/1.0)'
            })
            for entry in feed.entries[:20]:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass
                if pub_date and pub_date < cutoff:
                    continue
                title   = entry.get('title', '').strip()
                summary = re.sub(r'<[^>]+>', '', entry.get('summary', entry.get('description', ''))).strip()[:250]
                text_low = (title + ' ' + summary).lower()
                score = (sum(3 for kw in KEYWORDS_HIGH if kw in text_low) +
                         sum(1 for kw in KEYWORDS_MED if kw in text_low))
                if score >= 3:
                    date_str = f"{pub_date.day} {MESI_SHORT[pub_date.month]}" if pub_date else '—'
                    impact   = '🔴 CRITICO' if score >= 9 else ('🟠 ALTO' if score >= 5 else '🟡 MEDIO')
                    articles.append({'title': title, 'source': source_name, 'score': score,
                                     'impact': impact, 'summary': summary[:180], 'date_str': date_str})
        except Exception as e:
            print(f"  Errore feed {source_name}: {e}")
    articles.sort(key=lambda x: x['score'], reverse=True)
    seen, unique = set(), []
    for art in articles:
        norm = re.sub(r'\W+', ' ', art['title'].lower()).strip()
        words = set(norm.split())
        if not any(len(words & set(s.split())) / max(len(words), len(set(s.split())), 1) > 0.65 for s in seen):
            if len(art['title']) > 10:
                seen.add(norm); unique.append(art)
        if len(unique) >= 7:
            break
    return unique

print("\n[2/4] Recupero notizie RSS ultime 72 ore...")
weekly_news = get_weekly_news()
print(f"  Notizie trovate: {len(weekly_news)}")

print("\n[3/4] Tentativo Forex Factory...")
_ff_res = get_ff_calendar()
ff_events, ff_ok, ff_nota_reale = _ff_res

# ── ANALISI AI DINAMICA (Claude Haiku) ───────────────────────────────────────
print("\n[4/4] Generazione analisi AI...")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ai = None

if ANTHROPIC_API_KEY:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        news_text = ""
        if weekly_news:
            news_text = "\n\nNOTIZIE REALI DELLA SETTIMANA (da feed RSS finanziari):\n"
            for i, n in enumerate(weekly_news[:7], 1):
                news_text += f"{i}. [{n['impact']}] {n['title']} ({n['source']}, {n['date_str']})\n"

        prompt = f"""Sei l'analista macro di NexusGoldOne, servizio professionale di copytrading sull'oro (XAU/USD).
Oggi è {today.strftime('%A %d %B %Y')} — stai scrivendo il report settimanale.

DATI DI MERCATO REALI (aggiornati a oggi):
- XAU/USD (Oro): ${fmt(xau_price,0)} | Range: ${fmt(xau_low,0)}-${fmt(xau_high,0)}
- S&P 500: {fmt(spx_price,0)} | Range: {fmt(spx_low,0)}-{fmt(spx_high,0)}
- NASDAQ: {fmt(ndx_price,0)} | Range: {fmt(ndx_low,0)}-{fmt(ndx_high,0)}
- DXY: {fmt(dxy_price,2)} | Range: {fmt(dxy_low,2)}-{fmt(dxy_high,2)}
- WTI Crude Oil: ${fmt(wti_price,1)} | Range: ${fmt(wti_low,1)}-${fmt(wti_high,1)}
- XAG/USD (Argento): ${fmt(xag_price,2)}
- EUR/USD: {fmt(eur_price,4)}
- VIX (volatilità/paura): {fmt(vix_price,1)} ({vix_label})
- Rendimento Treasury 10Y USA: {fmt(tny_price,2)}%
- Prossima FOMC: {fomc_str}
- Prossima BCE: {ecb_str}
{news_text}
Settimana corrente: Lun {lun.day}, Mar {mar.day}, Mer {mer.day}, Gio {gio.day}, Ven {ven.day} {MESI_SHORT[ven.month]} {ven.year}

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
  "sp500_bullet_3": "<b>Opportunità:</b> opportunità specifiche nel contesto attuale",
  "ndx_bullet_1": "<b>NASDAQ:</b> {fmt(ndx_price,0)}. Commento sul movimento",
  "ndx_bullet_2": "<b>Driver positivi:</b> fattori positivi specifici attuali per il NASDAQ",
  "ndx_bullet_3": "<b>Rischio:</b> rischi specifici attuali per il settore tech",
  "dedollarizzazione_intro": "2-3 frasi aggiornate su de-dollarizzazione e acquisti banche centrali con dati reali",
  "cb_cina_acquisti": "~XX t/mese",
  "cb_cina_riserve": "X.XXX+ t",
  "cb_cina_trend": "trend 1-2 parole",
  "cb_india_acquisti": "~XX t/mese",
  "cb_india_riserve": "XXX+ t",
  "cb_india_trend": "trend 1-2 parole",
  "cb_brics_acquisti": "valore aggregato",
  "cb_brics_riserve": "percentuale riserve globali",
  "cb_brics_trend": "confronto storico",
  "cb_global_acquisti": "previsione anno {today.year}",
  "cb_global_riserve": "totale riserve globali",
  "cb_global_trend": "dato comparativo",
  "dazi_intro": "2-3 frasi sui dazi USA aggiornate a {today.strftime('%B %Y')} con misure reali in vigore",
  "dazi_bullet_1": "<b>Inflazione USA:</b> impatto reale dazi su PCE/CPI con dati attuali",
  "dazi_bullet_2": "<b>Azionario:</b> settori più colpiti con dati specifici",
  "dazi_bullet_3": "<b>Oro:</b> come i dazi supportano strutturalmente XAU/USD",
  "dazi_bullet_4": "<b>Opportunità:</b> come l'investitore può trarne vantaggio",
  "fed_bullet_1": "<b>Tassi:</b> range ATTUALE Fed con percentuale esatta e decisione più recente",
  "fed_bullet_2": "<b>Prossima FOMC:</b> data esatta e attese mercato",
  "fed_bullet_3": "<b>Attenzione:</b> dati macro specifici determinanti per il prossimo meeting",
  "fed_bullet_4": "<b>Nota:</b> tema rilevante attuale su Fed o leadership",
  "bce_bullet_1": "<b>Tassi BCE:</b> livello attuale e decisione recente con data",
  "bce_bullet_2": "<b>Prossima riunione BCE:</b> data esatta e scenario atteso",
  "cal_lun_evento": "dato/evento macro specifico e reale del lunedì",
  "cal_lun_mercati": "mercati impattati",
  "cal_lun_imp": "🟠 Alta",
  "cal_mar_evento": "dato/evento macro specifico del martedì",
  "cal_mar_mercati": "mercati impattati",
  "cal_mar_imp": "🟠 Alta",
  "cal_mer_evento": "dato/evento macro specifico del mercoledì",
  "cal_mer_mercati": "mercati impattati",
  "cal_mer_imp": "🔴 Critica",
  "cal_gio_evento": "dato/evento macro specifico del giovedì",
  "cal_gio_mercati": "mercati impattati",
  "cal_gio_imp": "🟠 Alta",
  "cal_ven_evento": "dato/evento macro specifico del venerdì",
  "cal_ven_mercati": "mercati impattati",
  "cal_ven_imp": "🟡 Media",
  "cal_nota": "nota specifica sul dato più importante della settimana",
  "outlook_intro": "2-3 frasi sull'outlook per l'oro con riferimenti ai prezzi reali e al contesto attuale",
  "outlook_bullet_1": "<b>XAU/USD:</b> supporto area $X.XXX, resistenza area $X.XXX. Scenario e proiezione specifica",
  "outlook_bullet_2": "<b>S&P 500:</b> livelli chiave specifici e scenario per la settimana",
  "outlook_bullet_3": "<b>Dati macro USA:</b> dato più importante della settimana e impatto atteso su Fed e oro",
  "outlook_bullet_4": "<b>Target analisti oro {today.year}:</b> previsioni aggiornate di almeno 3 banche con cifre reali",
  "outlook_bullet_5": "<b>Scenario base:</b> visione complessiva e bias direzionale per la settimana",
  "wti_intro": "2 frasi su WTI Crude Oil nel contesto attuale: prezzo, driver, correlazione con oro",
  "wti_bullet_1": "<b>Prezzo WTI:</b> livello attuale, variazione settimanale, range e driver principali",
  "wti_bullet_2": "<b>OPEC+ e offerta:</b> decisioni recenti o attese OPEC+, impatto su supply globale",
  "wti_bullet_3": "<b>Correlazione oro–petrolio:</b> come il movimento del WTI si riflette su XAU/USD questa settimana",
  "silver_bullet_1": "<b>XAG/USD (Argento):</b> prezzo attuale, ratio oro/argento, trend tecnico",
  "silver_bullet_2": "<b>Domanda industriale argento:</b> settori chiave (solare, EV, semiconduttori) e impatto sul prezzo"
}}"""

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
        print("  ✓ Analisi AI generata con successo!")

    except Exception as e:
        print(f"  Errore Claude API: {e}. Uso testo di fallback.")
        ai = None

# ── FALLBACK testo statico se Claude non disponibile ─────────────────────────
if ai is None:
    gold_str  = f"${fmt(xau_price,0)}"
    ratio_str = str(round(xau_price / xag_price)) if (xau_price and xag_price) else "N/D"
    ai = {
        "snapshot_commento": f"L'oro (XAU/USD) quota {gold_str} nella settimana {WEEK_SHORT}, con range {fmt(xau_low,0)}–{fmt(xau_high,0)}. S&amp;P 500 a {fmt(spx_price,0)}, DXY a {fmt(dxy_price,2)}. Il metallo giallo mantiene il trend rialzista strutturale sostenuto da acquisti banche centrali e incertezza geopolitica.",
        "geopolitica_intro": f"Il quadro geopolitico di {MESI[today.month]} {today.year} continua a sostenere la domanda di beni rifugio. Tensioni in Medio Oriente, guerra in Ucraina e politica commerciale USA mantengono elevata l'incertezza strutturale sui mercati globali.",
        "geo_bullet_1": "<b>Medio Oriente / Iran–USA:</b> Le tensioni nella regione restano elevate con monitoraggio costante delle infrastrutture energetiche. Ogni escalation si traduce in acquisti di oro come asset rifugio.",
        "geo_bullet_2": "<b>Russia–Ucraina:</b> Il conflitto prosegue senza segnali concreti di cessate il fuoco. La NATO mantiene il supporto militare all'Ucraina. L'incertezza geopolitica continua a sostenere i flussi verso il gold safe haven.",
        "geo_bullet_3": "<b>Cina–Taiwan–USA:</b> Tensioni commerciali con dazi reciproci in vigore. Restrizioni ai semiconduttori e alle terre rare creano incertezza sulle catene di fornitura globali.",
        "geo_bullet_4": "<b>De-dollarizzazione / BRICS+:</b> Le banche centrali BRICS+ continuano acquisti record di oro fisico per diversificare dal dollaro. Trend strutturale di medio-lungo termine per XAU/USD.",
        "geo_bullet_5": f"<b>Energia / Petrolio:</b> WTI a ${fmt(wti_price,0)}. OPEC+ mantiene i tagli produttivi. La volatilità del petrolio per ragioni geopolitiche supporta indirettamente l'oro come asset rifugio alternativo.",
        "geo_bullet_6": "<b>Dazi USA e guerra commerciale:</b> I dazi USA al 145% su molte importazioni cinesi e le ritorsioni di Pechino creano incertezza normativa strutturalmente positiva per XAU/USD.",
        "azionario_intro": f"I mercati azionari USA navigano in un contesto di dati macro contrastanti. S&amp;P 500 a {fmt(spx_price,0)}: la stagione degli utili e le attese Fed rimangono i driver principali.",
        "sp500_bullet_1": f"<b>S&amp;P 500 livelli chiave:</b> chiusura a {fmt(spx_price,0)}. Supporto in area {fmt(spx_low,0)}, resistenza in area {fmt(spx_high,0)}.",
        "sp500_bullet_2": "<b>Rischi principali:</b> Dazi e compressione margini aziendali in auto, farmaceutico e manifatturiero. Volatilità settoriale elevata.",
        "sp500_bullet_3": "<b>Opportunità:</b> Dati macro positivi o guidance utili sopra attese potrebbero sostenere i livelli attuali. Monitorare settori difensivi.",
        "ndx_bullet_1": f"<b>NASDAQ:</b> {fmt(ndx_price,0)}. Il settore tech reagisce a tensioni commerciali e dazi su semiconduttori.",
        "ndx_bullet_2": "<b>Driver positivi:</b> Aspettative utili solide per i principali titoli tech. AI e cloud computing mantengono trazione strutturale.",
        "ndx_bullet_3": "<b>Rischio:</b> Restrizioni export semiconduttori verso Cina. Valutazioni elevate in contesto di tassi alti.",
        "dedollarizzazione_intro": f"La domanda strutturale di oro da parte delle banche centrali rimane il pilastro del bull market. In {MESI[today.month]} {today.year} gli acquisti da PBOC, RBI e banche emergenti continuano ad accelerare la diversificazione dal dollaro.",
        "cb_cina_acquisti": "~25 t/mese", "cb_cina_riserve": "2.280+ t", "cb_cina_trend": "Acquisti consecutivi",
        "cb_india_acquisti": "~18 t/mese", "cb_india_riserve": "840+ t", "cb_india_trend": "Diversificazione USD",
        "cb_brics_acquisti": "~65 t/mese", "cb_brics_riserve": "17,8% riserve glob.", "cb_brics_trend": "Era 11,2% nel 2019",
        "cb_global_acquisti": f"~900 t (prev. {today.year})", "cb_global_riserve": "~36.500 t totali", "cb_global_trend": "Domanda ai massimi storici",
        "dazi_intro": f"La strategia tariffaria USA con dazi al 145% su molte importazioni cinesi mantiene pressione sulle catene di fornitura globali e sull'inflazione. L'incertezza normativa di {MESI[today.month]} {today.year} è strutturalmente positiva per XAU/USD.",
        "dazi_bullet_1": "<b>Inflazione USA:</b> I dazi mantengono il PCE sopra il target Fed del 2%, riducendo lo spazio per tagli. Impatto stimato +0,5%–1,5% sul CPI annuo.",
        "dazi_bullet_2": "<b>Azionario:</b> Volatilità settoriale elevata in auto, farmaceutico, elettronica. Margini compressi per imprese import-dipendenti.",
        "dazi_bullet_3": "<b>Oro:</b> Il contesto inflazionistico e l'incertezza dei dazi costituiscono supporto strutturale. Ogni rialzo dei prezzi riduce i tassi reali e aumenta l'attrattività dell'oro.",
        "dazi_bullet_4": "<b>Opportunità:</b> Ogni escalation commerciale amplifica la domanda di asset rifugio. Il copytrading NexusGoldOne su XAU/USD è posizionato per beneficiarne.",
        "fed_bullet_1": "<b>Tassi Fed:</b> Range attuale 4,25%–4,50%. Politica restrittiva in attesa di dati CPI/PCE più favorevoli.",
        "fed_bullet_2": f"<b>Prossima FOMC:</b> {fomc_str}. Mercati prezzano 2–3 tagli totali nel {today.year}. Il timing dipende da inflazione e occupazione.",
        "fed_bullet_3": "<b>Attenzione:</b> CPI, PCE e NFP determinanti per il prossimo meeting. Lettura sopra attese = rinvio tagli.",
        "fed_bullet_4": "<b>Nota:</b> Pressioni politiche sull'indipendenza Fed da monitorare. Interferenze executive aumenterebbero l'incertezza e la domanda di oro.",
        "bce_bullet_1": "<b>Tassi BCE:</b> Tasso deposito al 2,25%. Ciclo di allentamento monetario in corso in Europa dopo la serie di tagli.",
        "bce_bullet_2": f"<b>Prossima riunione BCE:</b> {ecb_str}. Atteso ulteriore taglio 25 bps se inflazione Eurozona continua a moderarsi.",
        "cal_lun_evento": f"Lun {lun.day} {MESI_SHORT[lun.month]}: Apertura mercati — monitoraggio geopolitica e flussi safe haven", "cal_lun_mercati": "Oro, DXY", "cal_lun_imp": "🟠 Alta",
        "cal_mar_evento": f"Mar {mar.day} {MESI_SHORT[mar.month]}: Fiducia consumatori Conference Board / Dichiarazioni membri Fed", "cal_mar_mercati": "Dollaro, Oro", "cal_mar_imp": "🟠 Alta",
        "cal_mer_evento": f"Mer {mer.day} {MESI_SHORT[mer.month]}: PMI manifatturiero / Scorte petrolio EIA", "cal_mer_mercati": "WTI, Dollaro, Oro", "cal_mer_imp": "🔴 Critica",
        "cal_gio_evento": f"Gio {gio.day} {MESI_SHORT[gio.month]}: Sussidi disoccupazione settimanali / PIL preliminare USA", "cal_gio_mercati": "Dollaro, Oro, Indici", "cal_gio_imp": "🟠 Alta",
        "cal_ven_evento": f"Ven {ven.day} {MESI_SHORT[ven.month]}: PCE Core / Sentiment consumatori U. Michigan", "cal_ven_mercati": "Fed, Dollaro, Oro", "cal_ven_imp": "🔴 Critica",
        "cal_nota": f"Il PCE Core di venerdì {ven.day} {MESI[ven.month]} è il dato più atteso: misura preferita dalla Fed per l'inflazione. Una lettura sopra le attese riduce la probabilità di tagli e può comprimere XAU/USD nel breve, ma il trend strutturale rialzista rimane intatto.",
        "outlook_intro": f"Il quadro macro-geopolitico rimane strutturalmente favorevole all'oro. XAU/USD a {gold_str} consolida sopra i supporti con bias rialzista confermato da acquisti banche centrali, de-dollarizzazione e incertezza geopolitica globale.",
        "outlook_bullet_1": f"<b>XAU/USD:</b> Supporto area {fmt(xau_low,0)}, resistenza principale {fmt(xau_high,0)}. Bias strutturalmente rialzista. Ogni correzione è opportunità di ingresso nel medio termine.",
        "outlook_bullet_2": f"<b>S&amp;P 500:</b> Area {fmt(spx_low,0)} come supporto chiave. La correlazione inversa con l'oro si amplifica in caso di dati macro deludenti.",
        "outlook_bullet_3": "<b>Dati macro USA:</b> PCE Core questa settimana determinante per le aspettative Fed. Lettura sopra attese = pressione short-term su oro ma positiva nel medio termine.",
        "outlook_bullet_4": f"<b>Target analisti oro {today.year}:</b> Goldman Sachs $5.000, UBS $4.500, JP Morgan $4.800. Consensus rivisto al rialzo dopo il rally sopra $4.000. Bull case $5.500+ se ciclo tagli Fed accelera.",
        "outlook_bullet_5": "<b>Scenario base:</b> Consolidamento sopra i supporti con possibili spike di volatilità su dati macro. Bias strutturale rialzista confermato. NexusGoldOne posizionato per catturare i movimenti direzionali su XAU/USD.",
        "wti_intro": f"Il WTI Crude Oil quota ${fmt(wti_price,0)} questa settimana. Dinamiche OPEC+ e tensioni in Medio Oriente guidano la volatilità. Correlazione con l'oro: un WTI alto per ragioni geopolitiche tende a supportare XAU/USD.",
        "wti_bullet_1": f"<b>WTI:</b> ${fmt(wti_price,0)}. Range settimana: ${fmt(wti_low,0)}–${fmt(wti_high,0)}. Driver: tensioni Medio Oriente e incertezza domanda globale.",
        "wti_bullet_2": f"<b>OPEC+:</b> Tagli produttivi confermati. Prossima riunione ministeriale da monitorare per segnali inversione su supply {today.year}.",
        "wti_bullet_3": "<b>Correlazione oro–petrolio:</b> Quando WTI sale per ragioni geopolitiche, l'oro beneficia come rifugio alternativo. Monitorare la correlazione settimanale.",
        "silver_bullet_1": f"<b>Argento XAG/USD:</b> ${fmt(xag_price,1)}. Ratio oro/argento: {ratio_str}:1. Storicamente conveniente vs oro. Trend tecnico segue XAU/USD con leva maggiore.",
        "silver_bullet_2": "<b>Domanda industriale:</b> Solare fotovoltaico, EV e semiconduttori mantengono forte domanda strutturale. Supporto al prezzo nel medio termine.",
    }

# ── PDF ───────────────────────────────────────────────────────────────────────
print("\nGenerazione PDF...")
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
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

def calendar_tbl_ff(events):
    """Tabella calendario da dati Forex Factory reali."""
    hs = ParagraphStyle('ch', fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.white, alignment=TA_CENTER, leading=12)
    cs = ParagraphStyle('cc', fontName='Helvetica', fontSize=8.5, textColor=TEXT_COLOR, leading=12, wordWrap='LTR')
    ds = ParagraphStyle('cd', fontName='Helvetica-Bold', fontSize=8.5, textColor=TEXT_COLOR, alignment=TA_CENTER, leading=12)
    ts = ParagraphStyle('ct', fontName='Helvetica', fontSize=8, textColor=DARK_GRAY, alignment=TA_CENTER, leading=12)
    rows = [[Paragraph('Giorno', hs), Paragraph('Orario (ET)', hs),
             Paragraph('Evento Macroeconomico USD', hs), Paragraph('Impatto', hs), Paragraph('Prev. / Prec.', hs)]]
    bgs = []
    for i, ev in enumerate(events[:20]):
        ic, it = (RED_IMPACT, 'ALTO') if ev['impact'] == 'High' else (ORG_IMPACT, 'MEDIO')
        is_ = ParagraphStyle(f'ci{i}', fontName='Helvetica-Bold', fontSize=8.5, textColor=ic, alignment=TA_CENTER, leading=12)
        rows.append([Paragraph(ev['day'], ds), Paragraph(ev['time'], ts),
                     Paragraph(ev['title'], cs), Paragraph(it, is_),
                     Paragraph(f"{ev['forecast']} / {ev['previous']}", ts)])
        bgs.append(LIGHT_GRAY if i % 2 == 1 else colors.white)
    t = Table(rows, colWidths=[CW*0.18, CW*0.12, CW*0.38, CW*0.12, CW*0.20])
    st = [('BACKGROUND',(0,0),(-1,0),DARK_NAVY), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
          ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
          ('LEFTPADDING',(0,0),(-1,-1),6), ('RIGHTPADDING',(0,0),(-1,-1),6),
          ('GRID',(0,0),(-1,-1),0.4,MID_GRAY), ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#BDC3C7'))]
    for i, bg in enumerate(bgs): st.append(('BACKGROUND',(0,i+1),(-1,i+1),bg))
    t.setStyle(TableStyle(st))
    return t

def calendar_tbl_ai():
    """Tabella calendario da AI fallback."""
    hs = ParagraphStyle('ah', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_CENTER, leading=12)
    ds = ParagraphStyle('ad', fontName='Helvetica-Bold', fontSize=9, textColor=TEXT_COLOR, alignment=TA_CENTER, leading=12)
    cs = ParagraphStyle('ac', fontName='Helvetica', fontSize=9, textColor=TEXT_COLOR, leading=12)
    def ic(text):
        t = text.upper()
        if 'CRITICA' in t or 'CRITICO' in t: return 'CRITICA', RED_IMPACT
        if 'ALTA' in t or 'ALTO' in t: return 'ALTA', ORG_IMPACT
        return 'MEDIA', YEL_IMPACT
    def ip(label, col, idx):
        s = ParagraphStyle(f'ai{idx}', fontName='Helvetica-Bold', fontSize=9, textColor=col, alignment=TA_CENTER, leading=12)
        return Paragraph(label, s)
    GIORNI_SHORT = {0:'Lun', 1:'Mar', 2:'Mer', 3:'Gio', 4:'Ven', 5:'Sab', 6:'Dom'}
    def gf(d): return f"{GIORNI_SHORT[d.weekday()]} {d.day} {MESI_SHORT[d.month]}"
    li, lc = ic(ai["cal_lun_imp"]); mi, mc = ic(ai["cal_mar_imp"])
    mei, mec = ic(ai["cal_mer_imp"]); gi, gc = ic(ai["cal_gio_imp"]); vi, vc = ic(ai["cal_ven_imp"])
    rows = [
        [Paragraph('Data', hs), Paragraph('Evento', hs), Paragraph('Mercati', hs), Paragraph('Importanza', hs)],
        [Paragraph(gf(lun), ds), Paragraph(ai["cal_lun_evento"], cs), Paragraph(ai["cal_lun_mercati"], cs), ip(li, lc, 0)],
        [Paragraph(gf(mar), ds), Paragraph(ai["cal_mar_evento"], cs), Paragraph(ai["cal_mar_mercati"], cs), ip(mi, mc, 1)],
        [Paragraph(gf(mer), ds), Paragraph(ai["cal_mer_evento"], cs), Paragraph(ai["cal_mer_mercati"], cs), ip(mei, mec, 2)],
        [Paragraph(gf(gio), ds), Paragraph(ai["cal_gio_evento"], cs), Paragraph(ai["cal_gio_mercati"], cs), ip(gi, gc, 3)],
        [Paragraph(gf(ven), ds), Paragraph(ai["cal_ven_evento"], cs), Paragraph(ai["cal_ven_mercati"], cs), ip(vi, vc, 4)],
    ]
    t = Table(rows, colWidths=[CW*0.16, CW*0.38, CW*0.25, CW*0.21])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),DARK_NAVY), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),6), ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),8), ('RIGHTPADDING',(0,0),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, LIGHT_GRAY]),
        ('GRID',(0,0),(-1,-1),0.5,MID_GRAY), ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#BDC3C7')),
    ]))
    return t

def news_tbl(articles):
    """Genera la tabella notizie per il PDF."""
    if not articles:
        return body("Nessuna notizia di alto impatto rilevata questa settimana dai feed monitorati.")
    hdr_style  = ParagraphStyle('ntbl_hdr', fontName='Helvetica-Bold', fontSize=8.5,
                     textColor=colors.white, alignment=TA_CENTER, leading=13)
    date_style = ParagraphStyle('ntbl_date', fontName='Helvetica', fontSize=8,
                     textColor=TEXT_COLOR, alignment=TA_CENTER, leading=13)
    cell_style = ParagraphStyle('ntbl_cell', fontName='Helvetica', fontSize=8.5,
                     textColor=TEXT_COLOR, leading=13, wordWrap='LTR')
    src_style  = ParagraphStyle('ntbl_src', fontName='Helvetica-Oblique', fontSize=8,
                     textColor=DARK_GRAY, leading=13)
    rows = [[Paragraph('Imp.', hdr_style), Paragraph('Data', hdr_style),
             Paragraph('Titolo (EN)', hdr_style), Paragraph('Fonte', hdr_style)]]
    row_bgs = []
    for i, art in enumerate(articles):
        if '🔴' in art['impact'] or 'CRITICO' in art['impact'].upper():
            ic_col, imp_text = RED_IMPACT, 'CRITICO'
        elif '🟠' in art['impact'] or 'ALTO' in art['impact'].upper():
            ic_col, imp_text = ORG_IMPACT, 'ALTO'
        else:
            ic_col, imp_text = YEL_IMPACT, 'MEDIO'
        imp_style = ParagraphStyle(f'ntbl_imp_{i}', fontName='Helvetica-Bold', fontSize=8.5,
                        textColor=ic_col, alignment=TA_CENTER, leading=13)
        # Escaping & per ReportLab Paragraph
        title_text = (art['title'][:80] + ('...' if len(art['title']) > 80 else '')).replace('&', '&amp;')
        src_text = art['source'].replace('Gold News', 'Gold').replace('Finance', 'Fin.').replace('Markets', 'Mkt')
        rows.append([Paragraph(imp_text, imp_style), Paragraph(art['date_str'], date_style),
                     Paragraph(title_text, cell_style), Paragraph(src_text, src_style)])
        row_bgs.append(LIGHT_GRAY if i % 2 == 1 else colors.white)
    t = Table(rows, colWidths=[CW*0.13, CW*0.09, CW*0.52, CW*0.26])
    style = [
        ('BACKGROUND',(0,0),(-1,0),DARK_NAVY), ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),6), ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),7), ('RIGHTPADDING',(0,0),(-1,-1),7),
        ('GRID',(0,0),(-1,-1),0.4,MID_GRAY), ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#BDC3C7')),
    ]
    for i, bg in enumerate(row_bgs):
        style.append(('BACKGROUND',(0,i+1),(-1,i+1),bg))
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
story.append(tbl(
    [['Asset', 'Prezzo Attuale', 'Min / Max Settimana'],
     xau_row, spx_row, ndx_row, dxy_row],
    [CW*0.38, CW*0.28, CW*0.34]
))
# Tabella indicatori aggiuntivi (solo se almeno uno è disponibile)
if eur_price is not None or vix_price is not None or tny_price is not None:
    story.append(S(0.08))
    story.append(sub("Indicatori Chiave"))
    story.append(tbl(
        [['Indicatore', 'Valore Attuale', 'Contesto'],
         eur_row, vix_row, tny_row],
        [CW*0.38, CW*0.28, CW*0.34]
    ))
story.append(S(0.1))
story.append(body(ai["snapshot_commento"]))

# SEZ 2 — AGENDA MACROECONOMICA USD (Forex Factory o AI fallback)
story.extend(sec(f"2. Agenda Macroeconomica USD — {WEEK_LABEL}"))
if ff_ok and ff_events:
    story.append(body(
        f"<b>Fonte: Forex Factory</b> — Dati reali aggiornati. "
        f"Tutti gli eventi USD ad alto e medio impatto per la settimana {WEEK_SHORT}. "
        f"Orari in ET (Eastern Time, UTC-4). "
        f"Gli eventi ad alto impatto possono muovere oro, dollaro e indici di punti percentuali in poche ore."
    ))
    story.append(S(0.08))
    story.append(calendar_tbl_ff(ff_events))
else:
    story.append(body(
        f"Principali eventi macroeconomici USA attesi questa settimana ({WEEK_SHORT}). "
        f"Gli appuntamenti ad alta importanza possono generare movimenti significativi su oro, dollaro e indici. "
        f"Orari indicativi — verificare su Forex Factory per i valori aggiornati."
    ))
    story.append(S(0.08))
    story.append(calendar_tbl_ai())
story.append(S(0.1))
_nota_finale = ff_nota_reale if ff_nota_reale else ai['cal_nota']
story.append(body(f"<b>Nota:</b> {_nota_finale}"))
# CondPageBreak: evita pagina bianca se la sezione finisce a metà pagina
story.append(CondPageBreak(8*cm))

# SEZ 2b — NOTIZIE FLASH ULTIME 72 ORE (solo se ci sono notizie)
if weekly_news:
    story.extend(sec("2b. Notizie Flash — Ultime 72 Ore"))
    story.append(body(
        f"Notizie di alto impatto dai principali feed finanziari globali, aggiornate al "
        f"{today.day} {MESI[today.month]} {today.year}. "
        f"Le notizie sono classificate per rilevanza (Critico / Alto / Medio) "
        f"in base all'impatto atteso su oro, dollaro e mercati."
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
story.append(S(0.1))

# SEZ 4 — MERCATI AZIONARI
story.extend(sec("4. Mercati Azionari — S&amp;P 500 e NASDAQ"))
story.append(body(ai["azionario_intro"]))
story.append(sub("S&amp;P 500"))
story.append(bul(ai["sp500_bullet_1"]))
story.append(bul(ai["sp500_bullet_2"]))
story.append(bul(ai["sp500_bullet_3"]))
story.append(sub("NASDAQ Composite"))
story.append(bul(ai["ndx_bullet_1"]))
story.append(bul(ai["ndx_bullet_2"]))
story.append(bul(ai["ndx_bullet_3"]))
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
story.append(tbl([
    ['Paese / Banca',      'Acquisti mensili',       'Riserve totali',         'Trend'],
    ['Cina (PBOC)',        ai["cb_cina_acquisti"],   ai["cb_cina_riserve"],    ai["cb_cina_trend"]],
    ['India (RBI)',        ai["cb_india_acquisti"],  ai["cb_india_riserve"],   ai["cb_india_trend"]],
    ['BRICS+ (aggreg.)',  ai["cb_brics_acquisti"],  ai["cb_brics_riserve"],   ai["cb_brics_trend"]],
    ['Globale (prev.)',   ai["cb_global_acquisti"], ai["cb_global_riserve"],  ai["cb_global_trend"]],
], [CW*0.27, CW*0.21, CW*0.24, CW*0.28]))
story.append(S(0.1))

# SEZ 6 — DAZI
story.extend(sec("6. Dazi USA e Guerra Commerciale"))
story.append(body(ai["dazi_intro"]))
story.append(bul(ai["dazi_bullet_1"]))
story.append(bul(ai["dazi_bullet_2"]))
story.append(bul(ai["dazi_bullet_3"]))
story.append(bul(ai["dazi_bullet_4"]))
story.append(CondPageBreak(7*cm))

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
story.append(S(0.1))
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
    "<i>DISCLAIMER: Il presente report è prodotto a esclusivo scopo informativo e non costituisce "
    "consulenza finanziaria, investimento consigliato o sollecitazione all'acquisto/vendita di strumenti "
    "finanziari. Le informazioni contenute si basano su fonti pubblicamente disponibili considerate "
    "affidabili alla data di redazione. NexusGoldOne non si assume alcuna responsabilità per decisioni "
    "prese sulla base di questo documento. Investire comporta rischi, inclusa la possibile perdita del capitale.</i>",
    ParagraphStyle('disc', fontName='Helvetica-Oblique', fontSize=7,
        textColor=DARK_GRAY, leading=10.5, alignment=TA_CENTER)
))

# BUILD PDF
doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN, topMargin=1.8*cm, bottomMargin=2.2*cm)
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(f"✓ PDF generato: {OUTPUT}")
print(f"  Oro: ${fmt(xau_price,0)} | VIX: {fmt(vix_price,1)} | 10Y: {fmt(tny_price,2)}%")
print(f"  FOMC: {fomc_str} | BCE: {ecb_str}")
print(f"  FF Calendar: {'SI (dati reali)' if ff_ok else 'NO (AI fallback)'} | Notizie RSS: {len(weekly_news)}")

# ── INVIO TELEGRAM ────────────────────────────────────────────────────────────
BOT_TOKEN      = os.environ.get("BOT_TOKEN")
CHANNEL_ID     = os.environ.get("CHANNEL_ID")
TOPIC_ID       = os.environ.get("TOPIC_ID", "2")
ADMIN_CHAT_ID  = os.environ.get("REVIEW_GROUP_ID", "-5122912249")

def send_admin_alert(token, chat_id, message):
    """Invia un messaggio privato all'admin in caso di errore — mai visibile sul canale."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=15
        )
    except Exception:
        pass

def send_document_with_retry(token, channel_id, topic_id, filepath, filename, caption, retries=3):
    """Invia il PDF con fino a 3 tentativi automatici."""
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with open(filepath, "rb") as f:
                resp = requests.post(url, data={
                    "chat_id":           channel_id,
                    "message_thread_id": topic_id,
                    "caption":           caption,
                    "parse_mode":        "Markdown",
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
    return last_error

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
        alert = (
            f"⚠️ *NexusGoldOne — Report NON inviato*\n\n"
            f"Il PDF `{FILENAME}` non è stato consegnato al canale.\n\n"
            f"*Errore:* {result}\n\n"
            f"Vai su GitHub Actions → Run workflow per ritentare manualmente."
        )
        send_admin_alert(BOT_TOKEN, ADMIN_CHAT_ID, alert)
        print(f"Alert privato inviato all'admin. Errore: {result}")
        exit(1)
