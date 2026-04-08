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

CHANNEL_ID = os.environ.get("CHANNEL_ID", "@NexusGoldOne")
MACRO_TOPIC_ID = 2

PDF_DIR = os.path.dirname(__file__)

PDF_APERTURA   = os.path.join(PDF_DIR, "2 Nexus One - Apertura conto.pdf")
PDF_SOFTWARE   = os.path.join(PDF_DIR, "1 Nexus One - Presentazione.pdf")
PDF_MANUALE    = os.path.join(PDF_DIR, "GoldFusion.pdf")
PDF_FAQ        = os.path.join(PDF_DIR, "NexusGoldOne_FAQ.pdf")


def get_latest_macro_pdf():
    pattern = os.path.join(PDF_DIR, "MACRO_Geopolitica_*.pdf")
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


WELCOME = (
    "Benvenuto in *NexusGoldOne* ⚡\n\n"
    "Seleziona l'area che ti interessa per ricevere tutte le informazioni e la guida per iniziare 👇🏻"
)

GUIDA = (
    "Guida per iniziare 🚀\n\n"
    "Ecco la guida completa per aprire il tuo conto. Una volta aperto il conto ed eseguito il deposito, "
    "contattaci su @SuppNexusGoldOne per ricevere il link di allacciamento con la guida.\n\n"
    "Per qualsiasi domanda scrivici direttamente.\n\n"
    "💬 @SuppNexusGoldOne"
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


async def send_weekly_macro(context: ContextTypes.DEFAULT_TYPE):
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
            filename="NexusGoldOne - Apertura conto.pdf"
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


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("macro", macro_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    tz_rome = pytz.timezone("Europe/Rome")
    send_time = datetime.time(hour=8, minute=0, second=0, tzinfo=tz_rome)

    app.job_queue.run_daily(
        callback=send_weekly_macro,
        time=send_time,
        days=(0,),
        name="weekly_macro_report"
    )

    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
