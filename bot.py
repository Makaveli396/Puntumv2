# OPCIÓN 1: SOLO ADMIN DEL BOT PUEDE AUTORIZAR
# La más segura - solo tú puedes autorizar

async def cmd_autorizar_admin_only(update, context):
    """Solo el admin del bot puede autorizar grupos"""
    # TU USER ID (cámbialo por tu ID real)
    ADMIN_BOT_ID = 123456789  # 👈 PON TU ID AQUÍ
    
    if update.effective_user.id != 5548909327:
        await update.message.reply_text(
            "🚫 **Solo el administrador del bot puede autorizar grupos**\n\n"
            "📞 Contacta a @tu_usuario para solicitar autorización"
        )
        return
    
    # Verificar que es un grupo
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Usa este comando en el grupo que quieres autorizar")
        return
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Grupo Sin Título"
    
    if is_chat_authorized(chat_id):
        await update.message.reply_text("✅ Este grupo ya está autorizado")
        return
    
    # Autorizar
    if authorize_chat(chat_id, chat_title):
        await update.message.reply_text(
            "🎉 **¡GRUPO AUTORIZADO POR ADMIN!** 🎉\n\n"
            f"🎬 **{chat_title}** ya puede usar CINEGRAM Puntum Bot\n\n"
            "🏷️ **Hashtags disponibles:**\n"
            "• `#aporte` • `#reseña` • `#crítica` • `#recomendación`\n\n"
            "🍿 **¡Que comience la diversión cinematográfica!**",
            parse_mode='Markdown'
        )
        print(f"[ADMIN] Grupo autorizado por admin: {chat_id} ({chat_title})")
    else:
        await update.message.reply_text("❌ Error al autorizar")

# ===================================================================

# OPCIÓN 2: SOLICITUD DE AUTORIZACIÓN (LA MÁS ELEGANTE)
# Los admins solicitan, tú apruebas fácilmente

async def cmd_solicitar_autorizacion(update, context):
    """Los admins del grupo solicitan autorización"""
    # Verificar que es un grupo
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Este comando solo funciona en grupos")
        return
    
    # Verificar que es admin del grupo
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, 
            update.effective_user.id
        )
        
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "❌ Solo los administradores del grupo pueden solicitar autorización"
            )
            return
    except Exception:
        await update.message.reply_text("❌ Error verificando permisos")
        return
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Grupo Sin Título"
    
    # Verificar si ya está autorizado
    if is_chat_authorized(chat_id):
        await update.message.reply_text("✅ Este grupo ya está autorizado")
        return
    
    # Verificar si ya hay una solicitud pendiente
    if is_authorization_pending(chat_id):
        await update.message.reply_text(
            "⏳ **Ya hay una solicitud pendiente para este grupo**\n\n"
            "El administrador del bot la revisará pronto."
        )
        return
    
    # Guardar solicitud
    save_authorization_request(chat_id, chat_title, update.effective_user.id, update.effective_user.username)
    
    # Notificar al admin del bot
    ADMIN_BOT_ID = 123456789  # 👈 TU ID
    try:
        await context.bot.send_message(
            ADMIN_BOT_ID,
            f"🔔 **NUEVA SOLICITUD DE AUTORIZACIÓN**\n\n"
            f"📝 **Grupo:** {chat_title}\n"
            f"🆔 **ID:** `{chat_id}`\n"
            f"👤 **Solicitante:** @{update.effective_user.username or 'sin username'}\n"
            f"📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"**Para autorizar:** `/aprobar {chat_id}`\n"
            f"**Para rechazar:** `/rechazar {chat_id}`",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"[ERROR] No se pudo notificar al admin: {e}")
    
    # Confirmar al solicitante
    await update.message.reply_text(
        "📩 **¡Solicitud enviada!**\n\n"
        "✅ Tu solicitud de autorización ha sido enviada al administrador del bot\n\n"
        "⏰ **Recibirás una respuesta pronto**\n"
        "🍿 Mientras tanto, prepara contenido cinematográfico genial para cuando se active!"
    )

# Funciones auxiliares para solicitudes
def save_authorization_request(chat_id, chat_title, user_id, username):
    """Guarda solicitud de autorización en BD"""
    import sqlite3
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # Crear tabla si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authorization_requests (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            requester_id INTEGER,
            requester_username TEXT,
            request_date TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    cursor.execute('''
        INSERT OR REPLACE INTO authorization_requests 
        (chat_id, chat_title, requester_id, requester_username, request_date, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (chat_id, chat_title, user_id, username, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def is_authorization_pending(chat_id):
    """Verifica si hay solicitud pendiente"""
    import sqlite3
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM authorization_requests WHERE chat_id = ? AND status = 'pending'", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

async def cmd_aprobar_grupo(update, context):
    """Comando para aprobar solicitudes (solo admin bot)"""
    ADMIN_BOT_ID = 123456789  # 👈 TU ID
    
    if update.effective_user.id != ADMIN_BOT_ID:
        await update.message.reply_text("❌ Solo el admin del bot puede usar este comando")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Uso: `/aprobar CHAT_ID`")
        return
    
    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de chat inválido")
        return
    
    # Obtener info de la solicitud
    import sqlite3
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT chat_title, requester_username FROM authorization_requests WHERE chat_id = ? AND status = 'pending'",
        (chat_id,)
    )
    result = cursor.fetchone()
    
    if not result:
        await update.message.reply_text("❌ No se encontró solicitud pendiente para ese chat")
        conn.close()
        return
    
    chat_title, requester_username = result
    
    # Autorizar el grupo
    if authorize_chat(chat_id, chat_title):
        # Marcar solicitud como aprobada
        cursor.execute(
            "UPDATE authorization_requests SET status = 'approved' WHERE chat_id = ?",
            (chat_id,)
        )
        conn.commit()
        
        # Notificar en el grupo
        try:
            await context.bot.send_message(
                chat_id,
                f"🎉 **¡SOLICITUD APROBADA!** 🎉\n\n"
                f"🎬 **{chat_title}** ya está autorizado para usar CINEGRAM Puntum Bot\n\n"
                f"🏷️ **Hashtags disponibles:**\n"
                f"• `#aporte` • `#reseña` • `#crítica` • `#recomendación`\n\n"
                f"🍿 **¡Que comience la competencia cinematográfica!**",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"[ERROR] No se pudo notificar aprobación al grupo: {e}")
        
        await update.message.reply_text(
            f"✅ **Grupo aprobado exitosamente**\n\n"
            f"📝 **Grupo:** {chat_title}\n"
            f"🆔 **ID:** `{chat_id}`\n"
            f"👤 **Solicitante:** @{requester_username}\n"
            f"🎬 El grupo ya puede usar el bot"
        )
        
    else:
        await update.message.reply_text("❌ Error al autorizar el grupo")
    
    conn.close()

async def cmd_rechazar_grupo(update, context):
    """Comando para rechazar solicitudes (solo admin bot)"""
    ADMIN_BOT_ID = 123456789  # 👈 TU ID
    
    if update.effective_user.id != ADMIN_BOT_ID:
        return
    
    if not context.args:
        await update.message.reply_text("❌ Uso: `/rechazar CHAT_ID [motivo]`")
        return
    
    try:
        chat_id = int(context.args[0])
        motivo = " ".join(context.args[1:]) or "No especificado"
    except ValueError:
        await update.message.reply_text("❌ ID de chat inválido")
        return
    
    # Marcar como rechazada
    import sqlite3
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE authorization_requests SET status = 'rejected' WHERE chat_id = ? AND status = 'pending'",
        (chat_id,)
    )
    
    if cursor.rowcount == 0:
        await update.message.reply_text("❌ No se encontró solicitud pendiente")
        conn.close()
        return
    
    conn.commit()
    conn.close()
    
    # Notificar rechazo al grupo
    try:
        await context.bot.send_message(
            chat_id,
            f"❌ **Solicitud de autorización rechazada**\n\n"
            f"**Motivo:** {motivo}\n\n"
            f"📞 Puedes contactar al administrador para más información"
        )
    except Exception:
        pass
    
    await update.message.reply_text(f"✅ Solicitud rechazada. Motivo: {motivo}")

async def cmd_ver_solicitudes(update, context):
    """Ver todas las solicitudes pendientes (solo admin bot)"""
    ADMIN_BOT_ID = 123456789  # 👈 TU ID
    
    if update.effective_user.id != ADMIN_BOT_ID:
        return
    
    import sqlite3
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT chat_id, chat_title, requester_username, request_date 
        FROM authorization_requests 
        WHERE status = 'pending'
        ORDER BY request_date DESC
    ''')
    
    solicitudes = cursor.fetchall()
    conn.close()
    
    if not solicitudes:
        await update.message.reply_text("📝 No hay solicitudes pendientes")
        return
    
    mensaje = "📋 **SOLICITUDES PENDIENTES**\n\n"
    
    for i, (chat_id, chat_title, username, fecha) in enumerate(solicitudes, 1):
        fecha_formatted = datetime.fromisoformat(fecha).strftime("%d/%m %H:%M")
        mensaje += (
            f"{i}. **{chat_title}**\n"
            f"   🆔 `{chat_id}`\n"
            f"   👤 @{username or 'sin username'}\n"
            f"   📅 {fecha_formatted}\n"
            f"   ✅ `/aprobar {chat_id}`\n"
            f"   ❌ `/rechazar {chat_id}`\n\n"
        )
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# ===================================================================

# OPCIÓN 3: NOTIFICACIÓN SIMPLE
# Los admins usan /autorizar, pero tú recibes notificación y puedes revocar

async def cmd_autorizar_con_notificacion(update, context):
    """Admins autorizan, pero el admin bot recibe notificación"""
    # Verificar que es un grupo
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ Este comando solo funciona en grupos")
        return
    
    # Verificar admin del grupo
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, 
            update.effective_user.id
        )
        
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Solo administradores del grupo pueden autorizar")
            return
    except Exception:
        await update.message.reply_text("❌ Error verificando permisos")
        return
    
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Grupo Sin Título"
    
    if is_chat_authorized(chat_id):
        await update.message.reply_text("✅ Este grupo ya está autorizado")
        return
    
    # Autorizar inmediatamente
    if authorize_chat(chat_id, chat_title):
        await update.message.reply_text(
            "🎉 **¡GRUPO AUTORIZADO!** 🎉\n\n"
            "🎬 CINEGRAM Puntum Bot ya está activo\n\n"
            "🏷️ Usa hashtags para sumar puntos:\n"
            "• `#aporte` • `#reseña` • `#crítica` • `#recomendación`\n\n"
            "🍿 ¡Que comience la diversión!",
            parse_mode='Markdown'
        )
        
        # Notificar al admin del bot
        ADMIN_BOT_ID = 123456789  # 👈 TU ID
        try:
            await context.bot.send_message(
                ADMIN_BOT_ID,
                f"🔔 **NUEVO GRUPO AUTORIZADO**\n\n"
                f"📝 **Grupo:** {chat_title}\n"
                f"🆔 **ID:** `{chat_id}`\n"
                f"👤 **Por:** @{update.effective_user.username or 'sin username'}\n"
                f"📅 **Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                f"**Para revocar:** `/revocar {chat_id}`",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"[ERROR] No se pudo notificar al admin: {e}")
        
        print(f"[AUTH] Grupo autorizado: {chat_id} ({chat_title}) por @{update.effective_user.username}")
    else:
        await update.message.reply_text("❌ Error al autorizar")

# CONFIGURACIÓN FINAL - OPCIÓN 2: SISTEMA DE SOLICITUDES
async def setup_bot():
    """Configurar bot con sistema de solicitudes (OPCIÓN 2)"""
    global bot_app
    
    bot_app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).post_init(post_init).build()
    
    # ========== OPCIÓN 2 ACTIVADA: SISTEMA DE SOLICITUDES ==========
    
    # Comando para que admins de grupos soliciten autorización
    bot_app.add_handler(CommandHandler("solicitar", cmd_solicitar_autorizacion))
    
    # Comandos para que TÚ manejes las solicitudes desde privado
    bot_app.add_handler(CommandHandler("aprobar", cmd_aprobar_grupo))
    bot_app.add_handler(CommandHandler("rechazar", cmd_rechazar_grupo))
    bot_app.add_handler(CommandHandler("solicitudes", cmd_ver_solicitudes))
    
    # Comandos de información
    bot_app.add_handler(CommandHandler("estado", cmd_estado_grupo))
    bot_app.add_handler(CommandHandler("grupos", cmd_grupos_autorizados))
    
    print("[INFO] ========== SISTEMA DE SOLICITUDES ACTIVADO ==========")
    print("[INFO] 📝 Para grupos nuevos: /solicitar")  
    print("[INFO] ✅ Para ti (admin): /aprobar ID")
    print("[INFO] ❌ Para ti (admin): /rechazar ID")
    print("[INFO] 📋 Para ti (admin): /solicitudes")
    print("[INFO] =====================================================")
    
    # IMPORTANTE: Crear tabla de solicitudes al inicio
    create_authorization_requests_table()
    
    print(f"[INFO] 🤖 Admin Bot ID requerido: Cambia '123456789' por tu ID real")
    # ========== HANDLERS PRINCIPALES CON AUTORIZACIÓN ==========
    bot_app.add_handler(CommandHandler("start", auth_required(cmd_start)))
    bot_app.add_handler(CommandHandler("help", auth_required(cmd_help)))
    bot_app.add_handler(CommandHandler("ranking", auth_required(cmd_ranking)))
    bot_app.add_handler(CommandHandler("reto", auth_required(cmd_reto)))
    bot_app.add_handler(CommandHandler("mipuntaje", auth_required(cmd_mipuntaje)))
    bot_app.add_handler(CommandHandler("miperfil", auth_required(cmd_miperfil)))
    bot_app.add_handler(CommandHandler("mirank", auth_required(cmd_mirank)))
    bot_app.add_handler(CommandHandler("test", auth_required(cmd_test)))
    
    # ========== COMANDOS ADMIN ADICIONALES ==========
    bot_app.add_handler(CommandHandler("nuevoreto", cmd_nuevo_reto))
    bot_app.add_handler(CommandHandler("testjob", cmd_test_job))
    bot_app.add_handler(CommandHandler("debug", cmd_debug))
    
    # ========== HANDLERS DE MENSAJES CON AUTORIZACIÓN ==========
    hashtag_filter = filters.TEXT & ~filters.COMMAND & filters.Regex(r'#\w+')
    bot_app.add_handler(MessageHandler(hashtag_filter, auth_required(handle_hashtags)), group=-1)
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required(spam_handler)), group=0)
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required(phrase_middleware)), group=1)
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auth_required(fallback_debug)), group=2)
    
    # Inicializar y configurar webhook
    await bot_app.initialize()
    await bot_app.start()
    
    webhook_url = f"{os.environ['RENDER_EXTERNAL_URL']}/webhook"
    result = await bot_app.bot.set_webhook(url=webhook_url)
    print(f"[INFO] Webhook configurado: {webhook_url} => {result}")
    
    return bot_app
def create_authorization_requests_table():
    """Crear tabla de solicitudes al inicializar el bot"""
    import sqlite3
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authorization_requests (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            requester_id INTEGER,
            requester_username TEXT,
            request_date TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[INFO] 📋 Tabla de solicitudes de autorización creada/verificada")
