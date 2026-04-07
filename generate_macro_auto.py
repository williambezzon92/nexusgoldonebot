#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NexusGoldOne — Generatore automatico Report Macro & Geopolitica
Gira ogni lunedì su GitHub Actions e invia il PDF al canale Telegram.
"""

import os
import requests
from datetime import date, timedelta

# ── DATE AUTOMATICHE ──────────────────────────────────────────────────────────
today    = date.today()
saturday = today + timedelta(days=5)

MESI = {
    1:"Gennaio", 2:"Febbraio", 3:"Marzo", 4:"Aprile",
    5:"Maggio", 6:"Giugno", 7:"Luglio", 8:"Agosto",
    9:"Settembre", 10:"Ottobre", 11:"Novembre", 12:"Dicembre"
}
MESI_SHORT = {
    1:"Gen", 2:"Feb", 3:"Mar", 4:"Apr", 5:"Mag", 6:"Giu",
    7:"Lug", 8:"Ago", 9:"Set", 10:"Ott", 11:"Nov", 12:"Dic"
}

WEEK_LABEL = f"Settimana dal {today.day:02d} al {saturday.day:02d} {MESI[saturday.month]} {saturday.year}"
WEEK_SHORT = f"{today.day:02d} {MESI_SHORT[today.month]} – {saturday.day:02d} {MESI_SHORT[saturday.month]} {saturday.year}"
FILENAME   = f"MACRO_Geopolitica_{today.strftime('%d-%m-%Y')}.pdf"
OUTPUT     = f"/tmp/{FILENAME}"

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
xau_price, xau_chg, xau_low, xau_high   = get_price("GC=F")
spx_price, spx_chg, spx_low, spx_high   = get_price("^GSPC")
ndx_price, ndx_chg, ndx_low, ndx_high   = get_price("^IXIC")
dxy_price, dxy_chg, dxy_low, dxy_high   = get_price("DX-Y.NYB")

def fmt(val, decimals=0, prefix=""):
    if val is None: return "N/D"
    return f"{prefix}{val:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_chg(val):
    if val is None: return "N/D"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%".replace(".", ",")

xau_row = [
    "XAU/USD (Oro)",
    f"~${fmt(xau_price, 0)}",
    fmt_chg(xau_chg),
    f"${fmt(xau_low, 0)} / ${fmt(xau_high, 0)}"
]
spx_row = [
    "S&P 500",
    f"~{fmt(spx_price, 0)}",
    fmt_chg(spx_chg),
    f"{fmt(spx_low, 0)} / {fmt(spx_high, 0)}"
]
ndx_row = [
    "NASDAQ Composite",
    f"~{fmt(ndx_price, 0)}",
    fmt_chg(ndx_chg),
    f"{fmt(ndx_low, 0)} / {fmt(ndx_high, 0)}"
]
dxy_row = [
    "DXY (Dollaro USA)",
    f"~{fmt(dxy_price, 2)}",
    fmt_chg(dxy_chg),
    f"{fmt(dxy_low, 2)} / {fmt(dxy_high, 2)}"
]

# ── PDF ───────────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, PageBreak)

GOLD       = colors.HexColor('#C9A84C')
DARK_NAVY  = colors.HexColor('#2C3E50')
LIGHT_GRAY = colors.HexColor('#F7F7F7')
MID_GRAY   = colors.HexColor('#D5D8DC')
DARK_GRAY  = colors.HexColor('#666666')
TEXT_COLOR = colors.HexColor('#1A1A1A')
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

# ── COSTRUZIONE STORY ─────────────────────────────────────────────────────────
story = []

# TITOLO
story.append(S(0.2))
story.append(Paragraph("NEXUSGOLDONE", ParagraphStyle('brand', fontName='Helvetica-Bold',
    fontSize=11, textColor=GOLD, alignment=TA_CENTER, spaceAfter=4)))
story.append(Paragraph("REPORT MACRO &amp; GEOPOLITICA", ParagraphStyle('maintitle',
    fontName='Helvetica-Bold', fontSize=26, textColor=TEXT_COLOR,
    alignment=TA_CENTER, leading=32, spaceAfter=0)))
story.append(S(0.25))
story.append(Paragraph(WEEK_LABEL, ParagraphStyle('weeklabel', fontName='Helvetica-Oblique',
    fontSize=11, textColor=GOLD, alignment=TA_CENTER, spaceAfter=0)))
story.append(S(0.35))
story.append(HRFlowable(width=CW, thickness=1.5, color=GOLD, spaceAfter=0))
story.append(S(0.4))

# SEZ 1 — SNAPSHOT
story.extend(sec("1. Snapshot Prezzi Settimanale"))
price_data = [
    ['Asset', 'Chiusura sett. prec.', 'Var. sett. prec.', 'Min / Max settim.'],
    xau_row, spx_row, ndx_row, dxy_row,
]
story.append(tbl(price_data, [CW*0.30, CW*0.22, CW*0.18, CW*0.30]))
story.append(S(0.2))
story.append(body(
    "L'oro mantiene la sua traiettoria strutturalmente rialzista sostenuta dalla domanda delle banche centrali "
    "e dall'incertezza geopolitica globale. I mercati azionari riflettono il quadro macro della settimana "
    "precedente, con volatilita' guidata dai dati macroeconomici USA e dalle tensioni commerciali. "
    "Il DXY rimane sotto pressione, elemento strutturalmente positivo per il metallo giallo."
))

# SEZ 2 — GEOPOLITICA
story.extend(sec("2. Geopolitica — Scenario Globale"))
story.append(body(
    "Il quadro geopolitico internazionale continua a sostenere la domanda di beni rifugio. "
    "Le tensioni nel Medio Oriente, le manovre militari nello Stretto di Taiwan e la guerra commerciale "
    "USA-Cina mantengono elevata l'incertezza strutturale sui mercati globali. "
    "Ogni escalation geopolitica si traduce storicamente in rafforzamento dell'oro nel breve-medio termine."
))
story.append(bul("<b>Medio Oriente:</b> situazione in evoluzione. Monitorare sviluppi su infrastrutture energetiche e approvvigionamento petrolifero globale."))
story.append(bul("<b>USA-Cina:</b> tensioni commerciali e militari nello Stretto di Taiwan. Impatto sulle catene di fornitura dei semiconduttori e sui mercati azionari tech."))
story.append(bul("<b>Guerra commerciale:</b> dazi USA su acciaio, alluminio, farmaci e prodotti cinesi mantengono pressione sull'inflazione globale e incertezza normativa."))
story.append(bul("<b>De-dollarizzazione:</b> BRICS+ continua ad accelerare la diversificazione dalle riserve in dollari verso l'oro fisico. Supporto strutturale di lungo termine per XAU/USD."))

story.append(PageBreak())

# SEZ 3 — MERCATI AZIONARI
story.extend(sec("3. Mercati Azionari — NASDAQ e S&amp;P 500"))
story.append(body(
    "I mercati azionari USA continuano a navigare in un contesto di dati macro contrastanti: "
    "mercato del lavoro solido da un lato, pressioni inflazionistiche e incertezza sui dazi dall'altro. "
    "La stagione degli utili e le aspettative Fed rimangono i principali driver di breve termine."
))
story.append(sub("S&amp;P 500"))
story.append(bul(f"<b>Chiusura settimana precedente:</b> {spx_row[1]} ({spx_row[2]}). Livelli chiave: resistenza 6.650-6.700; supporto in area 6.380."))
story.append(bul("<b>Rischi principali:</b> dazi su farmaci e manifatturiero comprimono i margini aziendali nel Q2. Volatilita' settoriale elevata."))
story.append(bul("<b>Opportunita':</b> dati macro positivi e utili Q1 sopra attese potrebbero spingere verso nuovi massimi nella seconda meta' dell'anno."))

story.append(sub("NASDAQ Composite"))
story.append(bul(f"<b>Chiusura settimana precedente:</b> {ndx_row[1]} ({ndx_row[2]}). Rimbalzo del settore tech e semiconduttori."))
story.append(bul("<b>Driver positivi:</b> allentamento aspettative sui dazi tech; utili Q1 attesi solidi per i principali titoli tecnologici."))
story.append(bul("<b>Rischio geopolitico:</b> tensioni Taiwan e guerre commerciali impattano le catene di fornitura dei semiconduttori."))

# SEZ 4 — DE-DOLLARIZZAZIONE
story.extend(sec("4. De-Dollarizzazione e Acquisti Banche Centrali"))
story.append(body(
    "La domanda strutturale di oro da parte delle banche centrali rimane il pilastro del bull market "
    "del metallo nel 2026. La diversificazione delle riserve dal dollaro verso l'oro fisico "
    "continua ad accelerare, con PBOC e RBI in testa agli acquisti globali."
))
cb_data = [
    ['Paese / Banca',    'Acquisti mensili',   'Riserve totali',     'Trend'],
    ['Cina (PBOC)',      '~25 t/mese',         '2.257+ t',           'Acquisti consecutivi'],
    ['India (RBI)',      '~18 t/mese',         '822+ t',             'Diversificazione USD'],
    ['BRICS+ (aggreg.)', '~60 t/mese',        '17,4% riserve glob.','Era 11,2% nel 2019'],
    ['Globale (prev.)', '~850 t (anno 2026)', '~36.000 t totali',   '$6 trl > US Treasuries'],
]
story.append(tbl(cb_data, [CW*0.27, CW*0.21, CW*0.24, CW*0.28]))
story.append(S(0.15))

# SEZ 5 — DAZI
story.extend(sec("5. Dazi USA e Guerra Commerciale"))
story.append(body(
    "La strategia tariffaria USA — acciaio, alluminio e rame al 50%, farmaci fino al 100% — "
    "mantiene pressione sulle catene di fornitura globali e sull'inflazione. "
    "L'incertezza normativa creata dalle misure e dalle successive contestazioni legali "
    "rende difficile per i mercati prezzare correttamente il rischio."
))
story.append(bul("<b>Inflazione USA:</b> i dazi mantengono il PCE sopra il target Fed del 2%, riducendo lo spazio per tagli dei tassi."))
story.append(bul("<b>Azionario:</b> volatilita' settoriale elevata in auto, farmaceutico e manifatturiero. Margini compressi nel Q2-Q3."))
story.append(bul("<b>Oro:</b> il contesto inflazionistico e l'incertezza creati dai dazi costituiscono supporto strutturale per XAU/USD."))
story.append(bul("<b>Opportunita':</b> ogni escalation commerciale aumenta la domanda di asset rifugio, rafforzando il caso rialzista per l'oro."))

story.append(PageBreak())

# SEZ 6 — BANCHE CENTRALI
story.extend(sec("6. Banche Centrali — Fed &amp; BCE"))
story.append(sub("Federal Reserve (USA)"))
story.append(bul("<b>Tassi:</b> range confermato al 3,50%-3,75%. Nessun taglio atteso prima del Q4 2026."))
story.append(bul("<b>Prossima decisione:</b> 28-29 aprile 2026. CME FedWatch: probabilita' alta di conferma dei tassi attuali."))
story.append(bul("<b>Attenzione:</b> dati CPI e PCE determinanti per il percorso dei tassi. Inflazione sopra 2,7% riduce probabilita' di tagli nel breve."))
story.append(bul("<b>Successione Powell:</b> Kevin Warsh nominato, profilo hawkish. Scenario sfavorevole a tagli rapidi nel 2026."))
story.append(sub("Banca Centrale Europea (BCE)"))
story.append(bul("<b>Tassi invariati:</b> inflazione in risalita per spinta energetica. BCE in modalita' 'wait and see'."))
story.append(bul("<b>Prossima riunione 30 aprile:</b> attesa stabilita' dei tassi finche' la crisi energetica non si normalizza."))

# SEZ 7 — CALENDARIO
story.extend(sec(f"7. Calendario Notizie — {WEEK_LABEL}"))
story.append(body(
    "Le principali pubblicazioni macroeconomiche e gli eventi geopolitici da monitorare questa settimana. "
    "I dati ad alto impatto possono generare movimenti significativi su oro, dollaro e indici azionari."
))

# Giorni della settimana con date calcolate automaticamente
lun = today
mar = today + timedelta(days=1)
mer = today + timedelta(days=2)
gio = today + timedelta(days=3)
ven = today + timedelta(days=4)

def gf(d): return f"{d.strftime('%a')} {d.day} {MESI_SHORT[d.month]}"

cal_data = [
    ['Data', 'Evento', 'Mercati', 'Importanza'],
    [gf(lun), 'Apertura mercati / aggiornamento geopolitica',      'Oro, Indici',       '🟠 Alta'],
    [gf(mar), 'Dati manifatturiero / dichiarazioni Fed',           'Dollaro, Oro',      '🟠 Alta'],
    [gf(mer), 'CPI USA / Scorte petrolio EIA',                     'Fed, Dollaro, Oro', '🔴 Critica'],
    [gf(gio), 'PPI USA / Sussidi disoccupazione settimanali',      'Dollaro, Oro',      '🟠 Alta'],
    [gf(ven), 'Sentiment consumatori / Dichiarazioni BCE',         'Euro, S&P 500, Oro','🟡 Media'],
]
story.append(tbl(cal_data, [CW*0.16, CW*0.38, CW*0.25, CW*0.21]))
story.append(S(0.15))
story.append(body(
    "<b>Nota:</b> il dato CPI del mercoledi' e' tipicamente il piu' atteso della settimana. "
    "Una lettura sopra le attese aumenta la probabilita' di un rinvio dei tagli Fed, "
    "generando pressione di breve sul metallo giallo ma rafforzando il caso strutturale rialzista. "
    "Monitorare anche eventuali sviluppi geopolitici imprevisti, principale catalizzatore di volatilita' sull'oro."
))
story.append(S(0.25))

# SEZ 8 — OUTLOOK
story.extend(sec(f"8. Outlook — {WEEK_LABEL}"))
story.append(body(
    "Il quadro macro-geopolitico rimane strutturalmente favorevole all'oro nel medio termine. "
    "La domanda delle banche centrali, la de-dollarizzazione in corso e le tensioni geopolitiche "
    "persistenti costituiscono un floor robusto per XAU/USD. Di seguito i livelli e scenari chiave:"
))
story.append(bul(f"<b>XAU/USD:</b> supporto in area ${fmt(xau_low, 0) if xau_low else '4.400-4.450'}, zona di forte interesse compratore; resistenza principale in area ${fmt(xau_high, 0) if xau_high else '4.700-4.800'}. Superamento della resistenza aprirebbe la strada verso area $5.000+."))
story.append(bul(f"<b>S&amp;P 500:</b> area {fmt(spx_low, 0) if spx_low else '6.350-6.400'} come supporto chiave della settimana. Tenuta = scenario neutro/positivo per l'azionario."))
story.append(bul("<b>Dati macro USA:</b> CPI e PPI determinanti per le aspettative Fed. Lettura sopra attese = pressione di breve sull'oro, opportunita' di acquisto nel medio termine."))
story.append(bul("<b>Target analisti oro:</b> UBS $6.200 entro settembre 2026; Goldman Sachs $5.400 fine anno; Commerzbank $5.000 Q4 2026."))
story.append(bul("<b>Scenario base:</b> consolidamento sopra i supporti con possibili spike di volatilita' legati a dati macro o eventi geopolitici. Bias strutturale rialzista confermato."))

story.append(S(0.2))

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
BOT_TOKEN  = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
TOPIC_ID   = os.environ.get("TOPIC_ID", "3")

if not BOT_TOKEN or not CHANNEL_ID:
    print("ATTENZIONE: BOT_TOKEN o CHANNEL_ID non configurati. PDF generato ma non inviato.")
else:
    caption = (
        f"📊 *NexusGoldOne — Report Macro & Geopolitica*\n\n"
        f"Analisi settimanale: geopolitica globale, banche centrali e price action sull'oro.\n"
        f"{WEEK_LABEL}\n\n"
        f"Buona lettura e buona settimana! ⚡\n\n"
        f"_NexusGoldOne_"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(OUTPUT, "rb") as f:
        resp = requests.post(url, data={
            "chat_id": CHANNEL_ID,
            "message_thread_id": TOPIC_ID,
            "caption": caption,
            "parse_mode": "Markdown",
        }, files={"document": (FILENAME, f, "application/pdf")}, timeout=60)

    result = resp.json()
    if result.get("ok"):
        print(f"PDF inviato con successo al canale Telegram: {FILENAME}")
    else:
        print(f"Errore Telegram: {result.get('description')} (code {result.get('error_code')})")
        exit(1)
