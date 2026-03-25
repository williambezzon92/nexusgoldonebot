import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "8274279855:AAFIvg_3Yo21YKrkoj7oleNqD3m8m0qLmEA")

# -----------------------------------------
#  CONFIGURAZIONE CANALE & GRUPPO REVISIONE
# -----------------------------------------
# ID del gruppo privato dove il ragazzo manda i PDF
# Ottienilo aggiungendo @userinfobot al gruppo e mandando /start
REVIEW_GROUP_ID = int(os.environ.get("REVIEW_GROUP_ID", "0"))

# ID del topic MERCATI e GEOPOLITICA nel canale (il numero dopo t.me/NexusGoldOne/)
MERCATI_TOPIC_ID = int(os.environ.get("MERCATI_TOPIC_ID", "0"))

# Username o ID del canale pubblico
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@NexusGoldOne")

# Dizionario temporaneo per tenere traccia dei PDF in attesa di approvazione
# { message_id: { "file_id": ..., "file_name": ..., "caption": ... } }
pending_docs = {}

# -----------------------------------------
#  PATH PDF
# -----------------------------------------

PDF_DIR = os.path.dirname(__file__)

PDF_APERTURA     = os.path.join(PDF_DIR, "2 Nexus One - Apertura conto.pdf")
PDF_SOFTWARE     = os.path.join(PDF_DIR, "1 Nexus One - Presentazione.pdf")
PDF_MANUALE      = os.path.join(PDF_DIR, "GoldFusion.pdf")
PDF_VEGAFUNDED   = os.path.join(PDF_DIR, "VegaFunded.pdf")
PDF_PROP         = os.path.join(PDF_DIR, "NexusGoldOne_PropFirm_FAQ.pdf")
PDF_FAQ          = os.path.join(PDF_DIR, "NexusGoldOne_FAQ.pdf")

# -----------------------------------------
#  MESSAGGI
# -----------------------------------------

WELCOME = (
    "Benvenuto in *NexusGoldOne* ⚡\n\n"
    "Seleziona l'area che ti interessa per ricevere tutte le informazioni e la guida per iniziare U0001f447U0001f3fb"
)

COPYTRADING = (
    "Copytrading U0001f4ca\n\n"
    "*NexusOne* — Expert Advisor che opera in automatico sull'oro (XAUUSD). "
    "Ogni operazione ha Stop Loss e Take Profit. Una volta allacciato lavora in autonomia, 24 ore su 24. "
    "Già 6 anni a mercato reale, progettato per conservare il capitale nel lungo termine.\n\n"
    "*GoldFusion* — Gestito da un trader professionista sull'oro (XAUUSD). "
    "Ogni operazione viene aperta con Stop Loss e Take Profit, in modalità intraday e multiday, "
    "e viene replicata automaticamente sul tuo conto.\n\n"
    "Trovi i PDF di presentazione di entrambe le strategie qui sotto.\n\n"
    "Per iniziare premi il pulsante qui sotto. "
    "Per qualsiasi domanda scrivici direttamente.\n\n"
    "U0001f4ac @SuppNexusGoldOne"
)

PROP = (
    "Prop Firm U0001f3c6\n\n"
    "Vuoi operare su capitali grandi senza rischiare i tuoi soldi? "
    "Con una Prop Firm paghi solo la quota della challenge e, se la superi, ricevi un conto finanziato "
    "fino a $200.000. Puoi anche usare il nostro servizio di passaggio automatico con garanzia 100%.\n\n"
    "U0001f39f️ Sconto 10% su VegaFunded con il codice: *GOLDFUSION*\n"
    "U0001f449 Registrati qui: https://dashboard.vegafunded.com/portal/referral/FDSNOFFY\n\n"
    "Nel PDF trovi tutte le informazioni e le domande frequenti.\n\n"
    "Per qualsiasi domanda scrivici direttamente.\n\n"
    "U0001f4ac @SuppNexusGoldOne"
)

COMINCIA = (
    "Inizia subito U0001f680\n\n"
    "Ecco la guida completa per aprire il tuo conto. "
    "Una volta registrato ed effettuato il deposito, contattaci su @SuppNexusGoldOne "
    "per ricevere il link di allacciamento alla strategia.\n\n"
    "Per qualsiasi domanda scrivici direttamente.\n\n"
    "U0001f4ac @SuppNexusGoldOne"
)

FAQ_MSG = (
    "Domande Frequenti ❓\n\n"
    "Qui sotto trovi le risposte alle domande più comuni sul Copytrading e sulla Prop Firm.\n\n"
    "U0001f4ac @SuppNexusGoldOne"
)

# -----------------------------------------
#  TASTIERE
# -----------------------------------------

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("U0001f680  Comincia ora",      callback_data="comincia")],
        [InlineKeyboardButton("U0001f4ca  Copytrading",       callback_data="copytrading")],
        [InlineKeyboardButton("U0001f3c6  Prop Firm",         callback_data="prop")],
        [InlineKeyboardButton("❓  Domande Frequenti", callback_data="faq")],
    ])

def section_keyboard(back_data):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("U0001f680  Comincia ora",   callback_data=f"comincia_from_{back_data}")],
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

    # -- Menu principale
    if data == "menu":
        await query.edit_message_text(WELCOME, reply_markup=main_keyboard(), parse_mode="Markdown")

    # -- Comincia ora (dal menu)
    elif data == "comincia":
        await send_comincia(query)

    # -- Comincia ora (dalle sezioni)
    elif data in ("comincia_from_copytrading", "comincia_from_prop"):
        await send_comincia(query)

    # -- Domande Frequenti (dalle sezioni)
    elif data in ("faq_from_copytrading", "faq_from_prop"):
        await query.edit_message_text(FAQ_MSG, reply_markup=back_menu_keyboard(), parse_mode="Markdown")
        await query.message.reply_document(
            document=open(PDF_FAQ, "rb"),
            filename="NexusGoldOne - Domande Frequenti.pdf"
        )

    # -- Copytrading
    elif data == "copytrading":
        await query.edit_message_text(COPYTRADING, reply_markup=section_keyboard("copytrading"), parse_mode="Markdown")
        await query.message.reply_document(
            document=open(PDF_SOFTWARE, "rb"),
            filename="NexusOne - Presentazione.pdf"
        )
        await query.message.reply_document(
            document=open(PDF_MANUALE, "rb"),
            filename="GoldFusion.pdf"
        )
        await query.message.reply_document(
            document=open(PDF_FAQ, "rb"),
            filename="NexusGoldOne - Domande Frequenti.pdf"
        )

    # -- Prop Firm
    elif data == "prop":
        await query.edit_message_text(PROP, reply_markup=section_keyboard("prop"), parse_mode="Markdown")
        await query.message.reply_document(
            document=open(PDF_VEGAFUNDED, "rb"),
            filename="VegaFunded.pdf"
        )
        await query.message.reply_document(
            document=open(PDF_PROP, "rb"),
            filename="NexusGoldOne - Prop Firm FAQ.pdf"
        )

    # -- Domande Frequenti
    elif data == "faq":
        await query.edit_message_text(FAQ_MSG, reply_markup=back_menu_keyboard(), parse_mode="Markdown")
        await query.message.reply_document(
            document=open(PDF_FAQ, "rb"),
            filename="NexusGoldOne - Domande Frequenti.pdf"
        )

# -----------------------------------------
#  GRUPPO REVISIONE — RICEZIONE PDF
# -----------------------------------------

async def review_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quando arriva un PDF nel gruppo di revisione, chiede approvazione con bottoni."""
    msg = update.message
    if not msg or not msg.document:
        return

    # Solo nel gruppo privato configurato
    if REVIEW_GROUP_ID == 0 or msg.chat_id != REVIEW_GROUP_ID:
        return

    doc = msg.document
    sender = msg.from_user.first_name or "Sconosciuto"

    # Salva il PDF in attesa di approvazione
    pending_docs[msg.message_id] = {
        "file_id":   doc.file_id,
        "file_name": doc.file_name or "documento.pdf",
        "caption":   msg.caption or "",
        "from":      sender,
    }

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅  Pubblica", callback_data=f"pub_{msg.message_id}"),
        InlineKeyboardButton("❌  Scarta",   callback_data=f"dis_{msg.message_id}"),
    ]])

    await msg.reply_text(
        f"U0001f4c4 Nuovo documento da *{sender}*\n"
        f"U0001f4ce `{doc.file_name}`\n\n"
        f"Vuoi pubblicarlo su *MERCATI e GEOPOLITICA*?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# -----------------------------------------
#  GRUPPO REVISIONE — APPROVAZIONE/SCARTO
# -----------------------------------------

async def review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce ✅ Pubblica e ❌ Scarta dal gruppo di revisione."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("pub_"):
        msg_id = int(data[4:])
        doc_info = pending_docs.pop(msg_id, None)

        if not doc_info:
            await query.edit_message_text("⚠️ Documento non trovato (già pubblicato o scartato).")
            return

        caption = doc_info["caption"] or "U0001f4ca Nuovo aggiornamento — *Mercati e Geopolitica*"
        await context.bot.send_document(
            chat_id=CHANNEL_ID,
            document=doc_info["file_id"],
            caption=caption,
            parse_mode="Markdown",
            message_thread_id=MERCATI_TOPIC_ID if MERCATI_TOPIC_ID != 0 else None,
        )

        await query.edit_message_text(
            f"✅ Pubblicato nel canale!\nU0001f4ce `{doc_info['file_name']}`",
            parse_mode="Markdown"
        )

    elif data.startswith("dis_"):
        msg_id = int(data[4:])
        pending_docs.pop(msg_id, None)
        await query.edit_message_text("❌ Documento scartato.")


# -----------------------------------------
#  AVVIO
# -----------------------------------------

def main():
    app = Application.builder().token(TOKEN).build()

    # Bot pubblico
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(?!pub_|dis_)"))

    # Gruppo revisione
    app.add_handler(MessageHandler(filters.Document.PDF, review_document))
    app.add_handler(CallbackQueryHandler(review_callback, pattern="^(pub_|dis_)"))

    app.run_polling()

if __name__ == "__main__":
    main()
