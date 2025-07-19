
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
from db import create_tables, add_points, get_user_stats, get_top10
from juegos import (
    initialize_games_system,
    cleanup_games_periodically,
    cmd_cinematrivia,
    cmd_adivinapelicula,
    cmd_emojipelicula,
    cmd_pista,
    cmd_rendirse,
    cmd_estadisticas_juegos,
    cmd_top_jugadores,
    handle_trivia_callback,
    handle_game_message
)
from sistema_autorizacion import (  # Si tienes funciones largas de autorización, mejor modularlas
    create_auth_tables, is_chat_authorized, authorize_chat,
    auth_required, cmd_solicitar_autorizacion, cmd_aprobar_grupo, cmd_ver_solicitudes
)
from comandos_basicos import (  # Esto también podrías modular si deseas
    cmd_start, cmd_help, cmd_ranking, cmd_miperfil, cmd_reto, handle_hashtags
)

async def post_init(application):
    commands = [
        BotCommand("start", "Iniciar bot y ver bienvenida"),
        BotCommand("help", "Ayuda y guía completa"),
        BotCommand("ranking", "Ver top 10 usuarios"),
        BotCommand("miperfil", "Ver mi perfil y estadísticas"),
        BotCommand("reto", "Ver reto diario"),
        BotCommand("solicitar", "Solicitar autorización (solo grupos)"),
        BotCommand("cinematrivia", "Trivia de películas"),
        BotCommand("adivinapelicula", "Adivina por pistas"),
        BotCommand("emojipelicula", "Adivina por emojis"),
        BotCommand("pista", "Pedir pista en juego activo"),
        BotCommand("rendirse", "Rendirse en juego activo"),
        BotCommand("estadisticasjuegos", "Ver tus estadísticas de juegos"),
        BotCommand("topjugadores", "Ranking global de juegos")
    ]
    await application.bot.set_my_commands(commands)
    print("[INFO] ✅ Comandos del bot configurados")

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("[ERROR] BOT_TOKEN no encontrado en variables de entorno")
        return

    print(f"[INFO] 🤖 Iniciando bot...")
    print(f"[INFO] 🔑 Token configurado: {token[:10]}...")

    create_tables()
    create_auth_tables()
    initialize_games_system()

    app = ApplicationBuilder().token(token).post_init(post_init).build()

    # Comandos
    app.add_handler(CommandHandler("solicitar", cmd_solicitar_autorizacion))
    app.add_handler(CommandHandler("aprobar", cmd_aprobar_grupo))
    app.add_handler(CommandHandler("solicitudes", cmd_ver_solicitudes))
    app.add_handler(CommandHandler("start", auth_required(cmd_start)))
    app.add_handler(CommandHandler("help", auth_required(cmd_help)))
    app.add_handler(CommandHandler("ranking", auth_required(cmd_ranking)))
    app.add_handler(CommandHandler("miperfil", auth_required(cmd_miperfil)))
    app.add_handler(CommandHandler("reto", auth_required(cmd_reto)))

    # Juegos
    app.add_handler(CommandHandler("cinematrivia", auth_required(cmd_cinematrivia)))
    app.add_handler(CommandHandler("adivinapelicula", auth_required(cmd_adivinapelicula)))
    app.add_handler(CommandHandler("emojipelicula", auth_required(cmd_emojipelicula)))
    app.add_handler(CommandHandler("pista", auth_required(cmd_pista)))
    app.add_handler(CommandHandler("rendirse", auth_required(cmd_rendirse)))
    app.add_handler(CommandHandler("estadisticasjuegos", auth_required(cmd_estadisticas_juegos)))
    app.add_handler(CommandHandler("topjugadores", auth_required(cmd_top_jugadores)))
    app.add_handler(CallbackQueryHandler(handle_trivia_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required(handle_game_message)))

    # Hashtags cinéfilos
    hashtag_filter = filters.TEXT & ~filters.COMMAND & filters.Regex(r'#\w+')
    app.add_handler(MessageHandler(hashtag_filter, auth_required(handle_hashtags)))

    print("[INFO] ✅ Handlers configurados")

    asyncio.create_task(cleanup_games_periodically())

    if os.environ.get("DEVELOPMENT"):
        print("[INFO] 🔄 Modo desarrollo - usando polling")
        app.run_polling()
    else:
        print("[INFO] 🌐 Modo producción - usando webhook")
        webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL', '')}/webhook"
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8000)),
            url_path="/webhook",
            webhook_url=webhook_url
        )

if __name__ == "__main__":
    main()
