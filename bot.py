import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("BOT_TOKEN", "8274279855:AAFIvg_3Yo21YKrkoj7oleNqD3m8m0qLmEA")
SUPP = '<a href="https://t.me/SuppNexusGoldOne">@SuppNexusGoldOne</a>'

# ── MESSAGGI ────────────────────────────────────────────────

WELCOME = (
    "Benvenuto in <b>NexusGoldOne</b> ⚡\n\n"
    "Seleziona una delle opzioni qui sotto per ricevere tutte le informazioni.\n\n"
    "Per info o per iniziare, scrivici direttamente:\n"
    "💬 " + SUPP
)

SOFTWARE_MSG = (
    "📊 <b>Copytrading Software — NexusOne</b>\n\n"
    "Qui sotto trovi il PDF completo con tutte le spiegazioni su come funziona "
    "il sistema di copytrading software.\n\n"
    "Per info o per iniziare, scrivici direttamente:\n"
    "💬 " + SUPP
)

MANUALE_MSG = (
    "📈 <b>Copytrading Manuale — GoldFusion</b>\n\n"
    "Qui sotto trovi il PDF completo con tutte le spiegazioni su come funziona "
    "il trading manuale GoldFusion.\n\n"
    "Per info o per iniziare, scrivici direttamente:\n"
    "💬 " + SUPP
)

INIZIA_MSG = (
    "🚀 <b>Comincia Ora</b>\n\n"
    "Qui sotto trovi la guida passo per passo per aprire il tuo conto e iniziare.\n\n"
    "Per info o per iniziare, scrivici direttamente:\n"
    "💬 " + SUPP
)

PDF_IN_ARRIVO = (
    "📋 <b>PDF in arrivo!</b>\n\n"
    "La guida sarà disponibile a breve.\n\n"
    "Per info o per iniziare, scrivici direttamente:\n"
    "💬 " + SUPP
)

INIZIA_PDF_MSG = (
    "🚀 <b>Comincia Ora</b>\n\n"
    "Per prima cosa cominciamo con l'apertura del conto.\n\n"
    "Una volta aperto il conto e verificato, scrivi al supporto per avere "
    "il link di allacciamento alla strategia e la guida di come allacciarsi.\n\n"
    "Per altre informazioni contattaci direttamente:\n"
    "💬 " + SUPP
)

# ── KEYBOARDS ───────────────────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Copytrading Software — NexusOne", callback_data="software")],
        [InlineKeyboardButton("📈 Copytrading Manuale — GoldFusion",  callback_data="manuale")],
        [InlineKeyboardButton("🚀 Comincia Ora",         callback_data="inizia")],
    ])

def software_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📎 Scarica PDF Software", callback_data="pdf_software")],
        [InlineKeyboardButton("🔙 Torna al menu",        callback_data="menu")],
    ])

def manuale_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📎 Scarica PDF Manuale",  callback_data="pdf_manuale")],
        [InlineKeyboardButton("🔙 Torna al menu",        callback_data="menu")],
    ])

def inizia_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📎 Guida Apertura Conto", callback_data="pdf_inizia")],
        [InlineKeyboardButton("🔙 Torna al menu",        callback_data="menu")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Torna al menu", callback_data="menu")],
    ])

# ── HANDLERS ───────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME,
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await query.edit_message_text(
            WELCOME,
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )

    elif data == "software":
        await query.edit_message_text(
            SOFTWARE_MSG,
            reply_markup=software_keyboard(),
            parse_mode="HTML"
        )

    elif data == "manuale":
        await query.edit_message_text(
            MANUALE_MSG,
            reply_markup=manuale_keyboard(),
            parse_mode="HTML"
        )

    elif data == "inizia":
        await query.edit_message_text(
            INIZIA_MSG,
            reply_markup=inizia_keyboard(),
            parse_mode="HTML"
        )

    elif data in ("pdf_software", "pdf_manuale"):
        await query.edit_message_text(
            PDF_IN_ARRIVO,
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )

    elif data == "pdf_inizia":
        await query.edit_message_text(
            INIZIA_PDF_MSG,
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )

# ── MAIN ────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
