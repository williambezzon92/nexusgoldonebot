import os
import glob
import logging
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN      = os.environ.get("BOT_TOKEN", "8274279855:AAFIvg_3Yo21YKrkoj7oleNqD3m8m0qLmEA")

# ID del canale/gruppo a cui mandare il report settimanale.
# Impostalo come variabile d'ambiente su Railway (es. -1001234567890)
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@NexusGoldOne")
MACRO_TOPIC_ID = 2  # Topic "Macro e Geopolitica" nel canale

# ─────────────────────────────────────────
#  PATH PDF
# ─────────────────────────────────────────

PDF_DIR = os.path.dirname(__file__)

PDF_APERTURA   = os.path.join(PDF_DIR, "2 Nexus One - Apertura conto.pdf")
PDF_GUIDA      = os.path.join(PDF_DIR, "Guida allacciamento.pdf")
PDF_SOFTWARE   = os.path.join(PDF_DIR, "1 Nexus One - Presentazione.pdf")
PDF_MANUALE    = os.path.join(PDF_DIR, "GoldFusion.pdf")
PDF_FAQ        = os.path.join(PDF_DIR, "NexusGoldOne_FAQ.pdf")


def get_latest_macro_pdf():
    """Restituisce il percorso del PDF macro più recente (MACRO_Geopolitica_*.pdf)."""
    pattern = os.path.join(PDF_DIR, "MACRO_Geopolitica_*.pdf")
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


# ─────────────────────────────────────────
#  MESSAGGI
# ─────────────────────────────────────────

WELCOME = (
    "Benvenuto in *NexusGoldOne* ⚡\n\n"
    "Seleziona l'area che ti interessa per ricevere tutte le informazioni e la guida per iniziare 👇🏻"
)

GUIDA = (
    "Guida per iniziare 🚀\n\n"
    "Ecco il link di registrazione a FpTrading:\n"
    "👉 [Registrati qui](https://portal.fptrading.com/register?fpm-affiliate-utm-source=IB&fpm-affiliate-agt=475978)\n\n"
    "Di seguito trovate la guida passo per passo 📄"
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
    "Per qualsiasi domanda trovi tutto nella sezione Domande Frequenti, oppure scrivici direttamente al supporto.\n\n"
    "💬 @SuppNexusGoldOne"
)

FAQ_MSG = (
    "Domande Frequenti ❓\n\n"
    "Qui sotto trovi le risposte alle domande più comuni sul Copytrading.\n\n"
    "💬 @SuppNexusGoldOne"
)

SUPPORTO_MSG = (
    "Supporto diretto 💬\n\n"
    "Scrivici direttamente, siamo qui per aiutarti in ogni passaggio.\n\n"
    "👉 @SuppNexusGoldOne"
)

# ─────────────────────────────────────────
#  TASTIERE
# ─────────────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋  Guida per iniziare",  callback_data="guida")],
        [InlineKeyboardButton("📊  Copytrading",         callback_data="copytrading")],
        [InlineKeyboardButton("❓  Domande Frequenti",   callback_data="faq")],
        [InlineKeyboardButton("💬  Supporto diretto",    callback_data="supporto")],
    ])

def back_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️  Torna al menu", callback_data="menu")],
    ])

# ─────────────────────────────────────────
#  REPORT MACRO SETTIMANALE
# ─────────────────────────────────────────

async def send_weekly_macro(context: ContextTypes.DEFAULT_TYPE):
    """
    Job schedulato: invia il report macro del lunedì mattina al canale/gruppo.
    Cerca automaticamente il PDF più recente MACRO_Geopolitica_*.pdf
    """
    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID non impostato — report settimanale non inviato.")
        return

    pdf_path = get_latest_macro_pdf()
    if not pdf_path:
        logger.error("Nessun PDF macro trovato — report settimanale non inviato.")
        return

    filename = os.path.basename(pdf_path)
    caption = (
        "📊 *NexusGoldOne — Report Settimanale*\n\n"
        "Geopolitica e mercato dell'oro: ecco l'analisi della settimana appena conclusa. "
        "Tutti i fattori macro che hanno mosso e muoveranno l'oro nei prossimi giorni.\n\n"
        "Buona lettura e buona settimana! ⚡\n\n"
        "_NexusGoldOne_"
    )

    try:
        await context.bot.send_document(
            chat_id=CHANNEL_ID,
            message_thread_id=MACRO_TOPIC_ID,
            document=open(pdf_path, "rb"),
            filename=filename,
            caption=caption,
            parse_mode="Markdown"
        )
        logger.info(f"Report macro inviato: {filename}")
    except Exception as e:
        logger.error(f"Errore invio report macro: {e}")


async def macro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /macro — invia manualmente il report macro più recente all'utente.
    Utile per testare o per richiedere il report fuori dal lunedì.
    """
    pdf_path = get_latest_macro_pdf()
    if not pdf_path:
        await update.message.reply_text("⚠️ Nessun report macro disponibile al momento.")
        return

    filename = os.path.basename(pdf_path)
    caption = (
        "📊 *NexusGoldOne — Report Macro Settimanale*\n\n"
        "Ecco l'analisi geopolitica e macro dell'oro più recente.\n\n"
        "_NexusGoldOne_"
    )
    await update.message.reply_document(
        document=open(pdf_path, "rb"),
        filename=filename,
        caption=caption,
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────
#  HANDLERS
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, reply_markup=main_keyboard(), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text(WELCOME, reply_markup=main_keyboard(), parse_mode="Markdown")

    elif data == "guida":
        await query.edit_message_text(GUIDA, reply_markup=back_menu_keyboard(), parse_mode="Markdown")
        await query.message.reply_document(
            document=open(PDF_APERTURA, "rb"),
            filename="NexusGoldOne - Apertura conto.pdf",
            caption="📋 Guida passo per passo per aprire il conto.\n\nUna volta aperto il conto ed eseguito il deposito, contattaci per ricevere il link di allacciamento.\n\n💬 @SuppNexusGoldOne"
        )

    elif data == "copytrading":
        await query.edit_message_text(COPYTRADING, reply_markup=back_menu_keyboard(), parse_mode="Markdown")
        await query.message.reply_document(
            document=open(PDF_SOFTWARE, "rb"),
            filename="NexusOne - Presentazione.pdf"
        )
        await query.message.reply_document(
            document=open(PDF_MANUALE, "rb"),
            filename="GoldFusion.pdf"
        )

    elif data == "faq":
        await query.edit_message_text(FAQ_MSG, reply_markup=back_menu_keyboard(), parse_mode="Markdown")
        await query.message.reply_document(
            document=open(PDF_FAQ, "rb"),
            filename="NexusGoldOne - Domande Frequenti.pdf"
        )

    elif data == "supporto":
        await query.edit_message_text(SUPPORTO_MSG, reply_markup=back_menu_keyboard(), parse_mode="Markdown")

# ─────────────────────────────────────────
#  AVVIO
# ─────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()

    # Handler comandi
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("macro", macro_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    # ── Job settimanale: ogni lunedì alle 08:00 ora italiana ──────────────────
    tz_rome = pytz.timezone("Europe/Rome")
    send_time = datetime.time(hour=8, minute=0, second=0, tzinfo=tz_rome)

    app.job_queue.run_daily(
        callback=send_weekly_macro,
        time=send_time,
        days=(0,),          # 0 = lunedì (Mon=0, Tue=1, ... Sun=6)
        name="weekly_macro_report"
    )
    logger.info("Job 'weekly_macro_report' schedulato — ogni lunedì alle 08:00 (Roma)")

    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
