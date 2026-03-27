import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8274279855:AAFIvg_3Yo21YKrkoj7oleNqD3m8m0qLmEA")

# -----------------------------------------
#  PATH PDF
# -----------------------------------------

PDF_DIR = os.path.dirname(__file__)

PDF_APERTURA   = os.path.join(PDF_DIR, "2 Nexus One - Apertura conto.pdf")
PDF_SOFTWARE   = os.path.join(PDF_DIR, "1 Nexus One - Presentazione.pdf")
PDF_MANUALE    = os.path.join(PDF_DIR, "GoldFusion.pdf")
PDF_VEGAFUNDED = os.path.join(PDF_DIR, "VegaFunded.pdf")
PDF_PROP       = os.path.join(PDF_DIR, "NexusGoldOne_PropFirm_FAQ.pdf")
PDF_FAQ        = os.path.join(PDF_DIR, "NexusGoldOne_FAQ.pdf")

# -----------------------------------------
#  MESSAGGI
# -----------------------------------------

WELCOME = (
    "Benvenuto in *NexusGoldOne* ⚡\n\n"
    "Seleziona l'area che ti interessa per ricevere tutte le informazioni e la guida per iniziare 👇🎻"
)

COPYTRADING = (
    "Copytrading 📊\n\n"
    "*NexusOne* — Expert Advisor che opera in automatico sull'oro (XAUUSD). "
    "Ogni operazione ha Stop Loss e Take Profit. Una volta allacciato lavora in autonomia, 24 ore su 24. "
    "Già 6 anni a mercato reale, progettato per conservare il capitale nel lungo termine.\n\n"
    "*GoldFusion* — Gestito da un trader professionista sull'oro (XAUUSD). "
    "Ogni operazione viene aperta con Stop Loss e Take Profit, in modalità intraday e multiday, "
    "e viene replicata automaticamente sul tuo conto.\n\n"
    "Trovi i PDF di presentazione di entrambe le strategie qui sotto.\n\n"
    "Per iniziare premi il pulsante qui sotto. "
    "Per qualsiasi domanda scrivici direttamente.\n\n"
    "💬 @SuppNexusGoldOne"
)

PROP = (
    "Prop Firm 🏆\n\n"
    "Vuoi operare su capitali grandi senza rischiare i tuoi soldi? "
    "Con una Prop Firm paghi solo la quota della challenge e, se la superi, ricevi un conto finanziato "
    "fino a $200.000. Puoi anche usare il nostro servizio di passaggio automatico con garanzia 100%.\n\n"
    "🎟️ Sconto 10% su VegaFunded con il codice: *GOLDFUSION*\n"
    "👉 Registrati qui: https://dashboard.vegafunded.com/portal/referral/FDSNOFFY\n\n"
    "Nel PDF trovi tutte le informazioni e le domande frequenti.\n\n"
    "Per qualsiasi domanda scrivici direttamente.\n\n"
    "💬 @SuppNexusGoldOne"
)

COMINCIA = (
    "Inizia subito 🚀\n\n"
    "Ecco la guida completa per aprire il tuo conto. "
    "Una volta registrato ed effettuato il deposito, contattaci su @SuppNexusGoldOne "
    "per ricevere il link di allacciamento alla strategia.\n\n"
    "Per qualsiasi domanda scrivici direttamente.\n\n"
    "💬 @SuppNexusGoldOne"
)

FAQ_MSG = (
    "Domande Frequenti ❓\n\n"
    "Qui sotto trovi le risposte alle domande più comuni sul Copytrading e sulla Prop Firm.\n\n"
    "💬 @SuppNexusGoldOne"
)

# -----------------------------------------
#  TASTIERE
# -----------------------------------------

def main_keyboard():
    return InlineKeyboardMarkup([
        [​InlineKeyboardButton("🚀  Comincia ora",      callback_data="comincia")],
        [InlineKeyboardButton("📊  Copytrading",       callback_data="copytrading")],
        [InlineKeyboardButton("🏆  Prop Firm",         callback_data="prop")],
        [InlineKeyboardButton("❓  Domande Frequenti", callback_data="faq")],
    ])

def section_keyboard(back_data):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀  Comincia ora",   callback_data=f"comincia_from_{back_data}")],
        [InlineKeyboardButton("⬅️  Torna al menu", callback_data="menu")],
    ])

def back_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️  Torna al menu", callback_data="menu")],
    ])

# -----------------------------------------
#  HELPERS
# -----------------------------------------

async def send_comincia(query):
    await query.edit_message_text(COMINCIA, reply_markup=back_menu_keyboard(), parse_mode="Markdown")
    await query.message.reply_document(
        document=open(PDF_APERTURA, "rb"),
        filename="NexusGoldOne - Apertura conto.pdf"
    )

# -----------------------------------------
#  HANDLERS
# -----------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, reply_markup=main_keyboard(), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text(WELCOME, reply_markup=main_keyboard(), parse_mode="Markdown")
    elif data == "comincia":
        await send_comincia(query)
    elif data in ("comincia_from_copytrading", "comincia_from_prop"):
        await send_comincia(query)
    elif data in ("faq_from_copytrading", "faq_from_prop"):
        await query.edit_message_text(FAQ_MSG, reply_markup=back_menu_keyboard(), parse_mode="Markdown")
        await query.message.reply_document(document=open(PDF_FAQ, "rb"), filename="NexusGoldOne - Domande Frequenti.pdf")
    elif data == "copytrading":
        await query.edit_message_text(COPYTRADING, reply_markup=section_keyboard("copytrading"), parse_mode="Markdown")
        await query.message.reply_document(document=open(PDF_SOFTWARE, "rb"), filename="NexusOne - Presentazione.pdf")
        await query.message.reply_document(document=open(PDF_MANUALE, "rb"), filename="GoldFusion.pdf")
        await query.message.reply_document(document=open(PDF_FAQ, "rb"), filename="NexusGoldOne - Domande Frequenti.pdf")
    elif data == "prop":
        await query.edit_message_text(PROP, reply_markup=section_keyboard("prop"), parse_mode="Markdown")
        await query.message.reply_document(document=open(PDF_VEGAFUNDED, "rb"), filename="VegaFunded.pdf")
        await query.message.reply_document(document=open(PDF_PROP, "rb"), filename="NexusGoldOne - Prop Firm FAQ.pdf")
    elif data == "faq":
        await query.edit_message_text(FAQ_MSG, reply_markup=back_menu_keyboard(), parse_mode="Markdown")
        await query.message.reply_document(document=open(PDF_FAQ, "rb"), filename="NexusGoldOne - Domande Frequenti.pdf")

# -----------------------------------------
#  AVVIO
# -----------------------------------------

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
