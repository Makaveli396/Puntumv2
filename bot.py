
#!/usr/bin/env python3

import os
import logging
import sqlite3
import asyncio
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# ==========================
# BASE DE DATOS PRINCIPAL
# ==========================

def create_tables():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# ==========================
# AUTORIZACIÓN DE GRUPOS
# ==========================

def create_auth_tables():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorized_chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            authorized_date TEXT DEFAULT CURRENT_TIMESTAMP,
            authorized_by INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorization_requests (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            requester_id INTEGER,
            requester_username TEXT,
            request_date TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

def is_chat_authorized(chat_id: int) -> bool:
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM authorized_chats WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def auth_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type == 'private':
            return await func(update, context)
        if not is_chat_authorized(update.effective_chat.id):
            await update.message.reply_text("❌ Grupo no autorizado. Usa /solicitar")
            return
        return await func(update, context)
    return wrapper

# ==========================
# COMANDOS SIMPLES
# ==========================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 ¡Bienvenido a Cinegram Puntum Bot!")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 Usa /start, /ranking, /miperfil, /reto, /cinematrivia, etc.")

# ==========================
# JUEGOS DE PELÍCULA (simples)
# ==========================

async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎲 Trivia iniciada (simulado)")

async def cmd_adivinapelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Adivina la película (simulado)")

async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎭 Emoji-película iniciada (simulado)")

async def cmd_pista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💡 Pista: es un clásico del cine")

async def cmd_rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏳️ Te has rendido, intenta otra vez!")

async def cmd_estadisticas_juegos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Tus estadísticas de juegos (simulado)")

async def cmd_top_jugadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏆 Top jugadores (simulado)")

async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 Respuesta recibida (simulado)")

async def handle_trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Respuesta registrada (simulado)")

async def cleanup_games_periodically():
    while True:
        print("[INFO] ⏳ Limpieza de juegos ejecutada")
        await asyncio.sleep(3600)

# ==========================
# CONFIGURACIÓN DEL BOT
# ==========================

async def post_init(application):
    commands = [
        BotCommand("start", "Iniciar bot"),
        BotCommand("help", "Ayuda y comandos"),
        BotCommand("cinematrivia", "Iniciar trivia"),
        BotCommand("adivinapelicula", "Juego de adivinar"),
        BotCommand("emojipelicula", "Adivina con emojis"),
        BotCommand("pista", "Pedir pista"),
        BotCommand("rendirse", "Rendirse del juego"),
        BotCommand("estadisticasjuegos", "Ver estadísticas"),
        BotCommand("topjugadores", "Ranking de jugadores")
    ]
    await application.bot.set_my_commands(commands)
    print("[INFO] ✅ Comandos configurados")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("[ERROR] BOT_TOKEN no encontrado")
        return

    create_tables()
    create_auth_tables()

    app = ApplicationBuilder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", auth_required(cmd_start)))
    app.add_handler(CommandHandler("help", auth_required(cmd_help)))
    app.add_handler(CommandHandler("cinematrivia", auth_required(cmd_cinematrivia)))
    app.add_handler(CommandHandler("adivinapelicula", auth_required(cmd_adivinapelicula)))
    app.add_handler(CommandHandler("emojipelicula", auth_required(cmd_emojipelicula)))
    app.add_handler(CommandHandler("pista", auth_required(cmd_pista)))
    app.add_handler(CommandHandler("rendirse", auth_required(cmd_rendirse)))
    app.add_handler(CommandHandler("estadisticasjuegos", auth_required(cmd_estadisticas_juegos)))
    app.add_handler(CommandHandler("topjugadores", auth_required(cmd_top_jugadores)))
    app.add_handler(CallbackQueryHandler(handle_trivia_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required(handle_game_message)))

    asyncio.create_task(cleanup_games_periodically())

    if os.environ.get("DEVELOPMENT"):
        print("[INFO] 🔄 Modo desarrollo")
        app.run_polling()
    else:
        print("[INFO] 🌐 Modo producción")
        webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook"
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8000)),
            url_path="/webhook",
            webhook_url=webhook_url
        )

if __name__ == "__main__":
    main()
