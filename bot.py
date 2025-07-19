# NUEVO: Agregar después de create_tables()

# Sistema de autorización simple - solo base de datos, sin variables de entorno
def is_chat_authorized(chat_id):
    """Verifica si un chat está autorizado usando la base de datos"""
    try:
        from db import get_chat_config
        config = get_chat_config(chat_id)
        return config and config.get('active', False)
    except Exception as e:
        print(f"[ERROR] Error verificando autorización: {e}")
        return False

def authorize_chat(chat_id, chat_title):
    """Autoriza un chat y lo guarda en la base de datos"""
    try:
        from db import set_chat_config
        set_chat_config(chat_id, chat_title, True, True)  # active=True, auto_jobs=True
        print(f"[INFO] Chat {chat_id} autorizado en BD")
        return True
    except Exception as e:
        print(f"[ERROR] Error autorizando chat: {e}")
        return False

def get_authorized_chats():
    """Obtiene todos los chats autorizados de la base de datos"""
    try:
        import sqlite3
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT chat_id, chat_title FROM chat_config WHERE active = 1")
        chats = cursor.fetchall()
        conn.close()
        
        return [(chat_id, title) for chat_id, title in chats]
    except Exception as e:
        print(f"[ERROR] Error obteniendo chats autorizados: {e}")
        return []

# NUEVO: Middleware de autorización simplificado
async def simple_auth_middleware(update, context):
    """Middleware simple que solo verifica la base de datos"""
    chat_id = update.effective_chat.id
    
    # Siempre permitir chats privados para comandos admin
    if update.effective_chat.type == 'private':
        return True
    
    # Verificar en base de datos
    if not is_chat_authorized(chat_id):
        print(f"[SECURITY] Chat no autorizado: {chat_id} ({update.effective_chat.title})")
        
        # Responder solo una vez
        try:
            await update.message.reply_text(
                "🚫 **Este grupo no está autorizado**\n\n"
                "Para usar CINEGRAM Puntum Bot:\n"
                "1️⃣ Un admin debe usar `/autorizar` aquí\n"
                "2️⃣ O contactar a @tu_usuario para autorización\n\n"
                "🎬 ¡Pronto podrás sumar puntos con tus aportes cinematográficos!",
                parse_mode='Markdown',
                reply_to_message_id=update.message.message_id
            )
        except Exception as e:
            print(f"[ERROR] Error enviando mensaje de autorización: {e}")
        
        return False
    
    return True

# MODIFICAR: Wrapper simplificado
def auth_required(handler_func):
    """Decorador simple para handlers que requieren autorización"""
    async def wrapper(update, context):
        if await simple_auth_middleware(update, context):
            return await handler_func(update, context)
    return wrapper

# NUEVOS COMANDOS SÚPER FÁCILES

async def cmd_autorizar(update, context):
    """
    Comando FÁCIL para autorizar el grupo actual
    Cualquier admin del grupo puede usarlo
    """
    # Verificar que es un grupo/supergrupo
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Este comando solo funciona en grupos")
        return
    
    # Verificar que el usuario es admin del grupo
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, 
            update.effective_user.id
        )
        
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "❌ Solo los administradores del grupo pueden autorizar el bot"
            )
            return
            
    except Exception as e:
        print(f"[ERROR] Error verificando admin: {e}")
        await update.message.reply_text("❌ Error verificando permisos de administrador")
        return
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Grupo Sin Título"
    
    # Verificar si ya está autorizado
    if is_chat_authorized(chat_id):
        await update.message.reply_text(
            "✅ Este grupo ya está autorizado para usar CINEGRAM Puntum Bot\n\n"
            "🎬 ¡Pueden empezar a usar hashtags para sumar puntos!"
        )
        return
    
    # Autorizar el grupo
    if authorize_chat(chat_id, chat_title):
        await update.message.reply_text(
            "🎉 **¡GRUPO AUTORIZADO!** 🎉\n\n"
            "🎬 **CINEGRAM Puntum Bot** ya está activo aquí\n\n"
            "📋 **Comandos disponibles:**\n"
            "• `/help` - Ver todos los comandos\n"
            "• `/ranking` - Ver clasificación actual\n"
            "• `/reto` - Ver reto semanal\n"
            "• `/mipuntaje` - Ver tus puntos\n\n"
            "🏷️ **Usa hashtags para sumar puntos:**\n"
            "• `#aporte` - Comparte contenido interesante\n"
            "• `#reseña` - Reseña películas/series\n"
            "• `#crítica` - Análisis profundo\n"
            "• `#recomendación` - Recomienda películas\n\n"
            "🍿 **¡Que empiece la competencia cinematográfica!**",
            parse_mode='Markdown'
        )
        
        print(f"[SUCCESS] Grupo autorizado: {chat_id} ({chat_title}) por {update.effective_user.username}")
    else:
        await update.message.reply_text("❌ Error al autorizar el grupo. Intenta de nuevo.")

async def cmd_desautorizar(update, context):
    """Comando para desautorizar el grupo actual (solo admins)"""
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Este comando solo funciona en grupos")
        return
    
    # Verificar admin
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, 
            update.effective_user.id
        )
        
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Solo administradores pueden desautorizar")
            return
            
    except Exception:
        await update.message.reply_text("❌ Error verificando permisos")
        return
    
    chat_id = update.effective_chat.id
    
    try:
        import sqlite3
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE chat_config SET active = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            "❌ **Grupo desautorizado**\n\n"
            "El bot ya no responderá a hashtags ni comandos aquí.\n"
            "Usa `/autorizar` si quieres reactivarlo."
        )
        
        print(f"[INFO] Grupo desautorizado: {chat_id} por {update.effective_user.username}")
        
    except Exception as e:
        print(f"[ERROR] Error desautorizando: {e}")
        await update.message.reply_text("❌ Error al desautorizar")

async def cmd_estado_grupo(update, context):
    """Ver el estado de autorización del grupo actual"""
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Chat Privado"
    
    if is_chat_authorized(chat_id):
        status = "✅ AUTORIZADO"
        mensaje = (
            f"📊 **Estado del Grupo**\n\n"
            f"🎬 **Grupo:** {chat_title}\n"
            f"🆔 **ID:** `{chat_id}`\n"
            f"📈 **Estado:** {status}\n\n"
            f"🎯 El bot está **activo** y responde a:\n"
            f"• Hashtags (#aporte, #reseña, etc.)\n"
            f"• Comandos (/ranking, /reto, etc.)\n"
            f"• Rankings automáticos semanales\n\n"
            f"🏆 ¡Sigan sumando puntos!"
        )
    else:
        status = "❌ NO AUTORIZADO"
        mensaje = (
            f"📊 **Estado del Grupo**\n\n"
            f"🎬 **Grupo:** {chat_title}\n"
            f"🆔 **ID:** `{chat_id}`\n"
            f"📈 **Estado:** {status}\n\n"
            f"⚠️ El bot **no está activo** aquí.\n"
            f"👤 Un admin puede usar `/autorizar` para activarlo."
        )
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_grupos_autorizados(update, context):
    """Lista todos los grupos autorizados (solo admins del bot)"""
    ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
    
    if not ADMIN_IDS or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Solo administradores del bot pueden ver esta información")
        return
    
    chats_autorizados = get_authorized_chats()
    
    if not chats_autorizados:
        await update.message.reply_text("📝 No hay grupos autorizados aún")
        return
    
    mensaje = "📋 **Grupos Autorizados CINEGRAM:**\n\n"
    
    for i, (chat_id, title) in enumerate(chats_autorizados, 1):
        # Intentar verificar si el bot sigue en el grupo
        try:
            chat_info = await context.bot.get_chat(chat_id)
            status = "✅"
            title = chat_info.title or title
        except Exception:
            status = "⚠️ (inaccesible)"
        
        mensaje += f"{i}. **{title}** {status}\n   `{chat_id}`\n\n"
    
    mensaje += f"📊 **Total:** {len(chats_autorizados)} grupos activos"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# MODIFICAR: setup_bot() con comandos fáciles
async def setup_bot():
    """Configura el bot con sistema de autorización fácil"""
    global bot_app
    
    bot_app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).post_init(post_init).build()
    
    # ========== COMANDOS DE AUTORIZACIÓN FÁCIL ==========
    bot_app.add_handler(CommandHandler("autorizar", cmd_autorizar))  # ¡SÚPER FÁCIL!
    bot_app.add_handler(CommandHandler("desautorizar", cmd_desautorizar))
    bot_app.add_handler(CommandHandler("estado", cmd_estado_grupo))
    
    # ========== COMANDOS PRINCIPALES CON AUTORIZACIÓN ==========
    bot_app.add_handler(CommandHandler("start", auth_required(cmd_start)))
    bot_app.add_handler(CommandHandler("help", auth_required(cmd_help)))
    bot_app.add_handler(CommandHandler("ranking", auth_required(cmd_ranking)))
    bot_app.add_handler(CommandHandler("reto", auth_required(cmd_reto)))
    bot_app.add_handler(CommandHandler("mipuntaje", auth_required(cmd_mipuntaje)))
    bot_app.add_handler(CommandHandler("miperfil", auth_required(cmd_miperfil)))
    bot_app.add_handler(CommandHandler("mirank", auth_required(cmd_mirank)))
    bot_app.add_handler(CommandHandler("test", auth_required(cmd_test)))
    
    # ========== COMANDOS ADMIN (funcionan en privado) ==========
    bot_app.add_handler(CommandHandler("grupos", cmd_grupos_autorizados))
    bot_app.add_handler(CommandHandler("nuevoreto", cmd_nuevo_reto))
    bot_app.add_handler(CommandHandler("testjob", cmd_test_job))
    bot_app.add_handler(CommandHandler("debug", cmd_debug))
    
    # ========== HANDLERS DE MENSAJES CON AUTORIZACIÓN ==========
    hashtag_filter = filters.TEXT & ~filters.COMMAND & filters.Regex(r'#\w+')
    bot_app.add_handler(MessageHandler(hashtag_filter, auth_required(handle_hashtags)), group=-1)
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required(spam_handler)), group=0)
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required(phrase_middleware)), group=1)
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required(fallback_debug)), group=2)
    
    print("[INFO] ========== SISTEMA DE AUTORIZACIÓN FÁCIL ACTIVADO ==========")
    print("[INFO] 🎯 Comandos para autorización:")
    print("[INFO] - /autorizar - Cualquier admin puede autorizar su grupo")
    print("[INFO] - /estado - Ver si el grupo está autorizado")
    print("[INFO] - /grupos - Listar grupos autorizados (admin bot)")
    print("[INFO] ============================================================")
    
    # Resto igual...
    await bot_app.initialize()
    await bot_app.start()
    
    webhook_url = f"{os.environ['RENDER_EXTERNAL_URL']}/webhook"
    result = await bot_app.bot.set_webhook(url=webhook_url)
    print(f"[INFO] Webhook configurado: {webhook_url} => {result}")
    
    return bot_app
