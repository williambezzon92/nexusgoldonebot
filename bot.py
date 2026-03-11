import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8274279855:AAFIvg_3Yo21YKrkoj7oleNqD3m8m0qLmEA")

SUPP = '<a href="https://t.me/SuppNexusGoldOne">@SuppNexusGoldOne</a>'

# ─────────────────────────────────────────
#  MESSAGGI
# ─────────────────────────────────────────

WELCOME = (
    "Benvenuti in NexusGoldOne ⚡\n\n"
    "Qua sotto si trovano tutte le informazioni necessarie.\n\n"
    "Se non bastassero o volete approfondire altro scrivete al nostro supporto: "
    + SUPP
)

SOFTWARE = (
    "Copytrading Software 🤖\n\n"
    "Trovi tutta la spiegazione su come funziona nel PDF qui sopra.\n\n"
    "Per qualsiasi domanda scrivici qui:\n"
    "💬 " + SUPP + "\n\n"
    "Altrimenti, qui sotto trovi il PDF con la guida completa "
    "per l’apertura del conto ⬇️"
)

MANUALE = (
    "Copytrading Manuale 📊\n\n"
    "Trovi tutta la spiegazione su come funziona nel PDF qui sopra.\n\n"
    "Per qualsiasi domanda scrivici qui:\n"
    "💬 " + SUPP + "\n\n"
    "Altrimenti, qui sotto trovi il PDF con la guida completa "
    "per l’apertura del conto ⬇️"
)

PDF_IN_ARRIVO = (
    "📋 PDF in arrivo!\n\n"
    "La guida sarà disponibile a breve.\n"
    "Per informazioni nel frattempo scrivici:\n"
    "💬 " + SUPP
)

PROP_INTRO = (
    "Prop Firm 🏆\n\n"
    "Vuoi operare su capitali grandi senza rischiare i tuoi soldi?\n"
    "Scopri come funziona e come iniziare ⬇️"
)

PROP_COSE = (
    "Cos’è una Prop Firm? 🏦\n\n"
    "Una Prop Firm è una società che ti mette a disposizione\n"
    "un capitale elevato per fare trading — senza rischiare\n"
    "i tuoi soldi personali.\n\n"
    "Come funziona:\n"
    "1️⃣  Superi una challenge dimostrando le tue capacità\n"
    "2️⃣  La Prop Firm ti assegna un conto finanziato\n"
    "     (es. 10.000€, 50.000€, 100.000€)\n"
    "3️⃣  Operi con il loro capitale\n"
    "4️⃣  Dividi i profitti con loro (profit split)\n\n"
    "🎯 Ideale per chi vuole fare trading su capitali importanti\n"
    "rischiando solo la quota di iscrizione alla challenge."
)

PROP_VEGA = (
    "VegaFunded 🔥\n\n"
    "VegaFunded è la Prop Firm che usiamo e consigliamo.\n\n"
    "✅  Personalizzazione del conto in base alle tue esigenze\n"
    "✅  Profit split aumentato o giorni di prelievo ridotti\n"
    "✅  Regole chiare, pensate per formare trader professionisti\n\n"
    "Per domande sulla scelta del conto:\n"
    "💬 " + SUPP
)

PROP_SCONTO = (
    "Sconto 10% su VegaFunded 🎟️\n\n"
    "1️⃣  Iscriviti tramite questo link:\n"
    "https://dashboard.vegafunded.com/portal/referral/FDSNOFFY\n\n"
    "2️⃣  Al pagamento inserisci il codice promo:\n"
    "🟡  GOLDFUSION\n\n"
    "Lo sconto si applica automaticamente su qualsiasi conto.\n\n"
    "Hai dubbi sulla scelta del conto?\n"
    "💬 " + SUPP
)

PROP_PASSAGGIO = (
    "Passaggio Automatico ⚡\n\n"
    "Non vuoi passare la challenge da solo? Ci pensiamo noi.\n\n"
    "I nostri tecnici gestiranno l’intera challenge al posto tuo.\n\n"
    "Come funziona:\n"
    "1️⃣  Acquisti la prop firm\n"
    "2️⃣  Ci fornisci nome, cognome e dati del conto\n"
    "3️⃣  I nostri tecnici gestiscono tutto\n"
    "4️⃣  Conto finanziato pronto 🎯\n\n"
    "💰 Costo del servizio: 800€\n\n"
    "✅ Passaggio garantito al 100%\n"
    "Se non superiamo la challenge, rimborsiamo l’intero costo del servizio.\n\n"
    "💡 Consiglio: scegli sempre la Step 1 (fase singola)\n"
    "per un passaggio più rapido ed efficiente.\n\n"
    "Per prenotare o avere maggiori informazioni:\n"
    "💬 " + SUPP
)

PROP_PARLA = (
    "Parla con noi 💬\n\n"
    "Il nostro team è disponibile per rispondere a qualsiasi\n"
    "domanda e guidarti passo passo.\n\n"
    "Scrivici qui:\n"
    "💬 " + SUPP
)

# ─────────────────────────────────────────
#  TASTIERE
# ─────────────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣  Copytrading Software", callback_data="software")],
        [InlineKeyboardButton("2️⃣  Copytrading Manuale",  callback_data="manuale")],
        [InlineKeyboardButton("3️⃣  Prop Firm",            callback_data="prop")],
    ])

def software_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚  Come funziona → PDF",       callback_data="pdf_come_funziona_sw")],
        [InlineKeyboardButton("📋  Guida apertura conto → PDF", callback_data="pdf_conto_sw")],
        [InlineKeyboardButton("⬅️  Torna al menu",                   callback_data="menu")],
    ])

def manuale_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚  Come funziona → PDF",       callback_data="pdf_come_funziona_man")],
        [InlineKeyboardButton("📋  Guida apertura conto → PDF", callback_data="pdf_conto_man")],
        [InlineKeyboardButton("⬅️  Torna al menu",                   callback_data="menu")],
    ])

def prop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❓  Cos’è una Prop Firm?",                  callback_data="prop_cose")],
        [InlineKeyboardButton("🏆  Come funziona VegaFunded?",             callback_data="prop_vega")],
        [InlineKeyboardButton("🎟️  Come ottengo lo sconto?",               callback_data="prop_sconto")],
        [InlineKeyboardButton("⚡  Come funziona il passaggio automatico?", callback_data="prop_passaggio")],
        [InlineKeyboardButton("💬  Parla con noi",                          callback_data="prop_parla")],
        [InlineKeyboardButton("⬅️  Torna al menu",                          callback_data="menu")],
    ])

def back_prop_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️  Torna a Prop Firm", callback_data="prop")],
        [InlineKeyboardButton("🏠  Menu principale",   callback_data="menu")],
    ])

def back_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️  Torna al menu", callback_data="menu")],
    ])

# ─────────────────────────────────────────
#  HANDLERS
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, reply_markup=main_keyboard(), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text(WELCOME, reply_markup=main_keyboard(), parse_mode="HTML")

    elif data == "software":
        await query.edit_message_text(SOFTWARE, reply_markup=software_keyboard(), parse_mode="HTML")

    elif data == "manuale":
        await query.edit_message_text(MANUALE, reply_markup=manuale_keyboard(), parse_mode="HTML")

    elif data == "prop":
        await query.edit_message_text(PROP_INTRO, reply_markup=prop_keyboard(), parse_mode="HTML")

    elif data == "prop_cose":
        await query.edit_message_text(PROP_COSE, reply_markup=back_prop_keyboard(), parse_mode="HTML")

    elif data == "prop_vega":
        await query.edit_message_text(PROP_VEGA, reply_markup=back_prop_keyboard(), parse_mode="HTML")

    elif data == "prop_sconto":
        await query.edit_message_text(PROP_SCONTO, reply_markup=back_prop_keyboard(), parse_mode="HTML")

    elif data == "prop_passaggio":
        await query.edit_message_text(PROP_PASSAGGIO, reply_markup=back_prop_keyboard(), parse_mode="HTML")

    elif data == "prop_parla":
        await query.edit_message_text(PROP_PARLA, reply_markup=back_prop_keyboard(), parse_mode="HTML")

    elif data in ("pdf_come_funziona_sw", "pdf_come_funziona_man",
                  "pdf_conto_sw", "pdf_conto_man"):
        await query.edit_message_text(PDF_IN_ARRIVO, reply_markup=back_menu_keyboard(), parse_mode="HTML")

# ─────────────────────────────────────────
#  AVVIO
# ─────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
