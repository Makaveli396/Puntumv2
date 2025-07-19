#!/usr/bin/env python3
import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters,
    ContextTypes
)
from db import create_tables, add_points, get_user_stats, get_top10

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== SISTEMA DE AUTORIZACIÓN ==========

def create_auth_tables():
    """Crear tablas de autorización"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authorized_chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            authorized_date TEXT DEFAULT CURRENT_TIMESTAMP,
            authorized_by INTEGER
        )
    ''')
    
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
    print("[INFO] 📋 Tablas de autorización creadas/verificadas")

def is_chat_authorized(chat_id: int) -> bool:
    """Verificar si un chat está autorizado"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM authorized_chats WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def authorize_chat(chat_id: int, chat_title: str, authorized_by: int = None) -> bool:
    """Autorizar un chat"""
    try:
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR REPLACE INTO authorized_chats (chat_id, chat_title, authorized_by) VALUES (?, ?, ?)",
            (chat_id, chat_title, authorized_by)
        )
        
        conn.commit()
        conn.close()
        print(f"[AUTH] Chat autorizado: {chat_id} ({chat_title})")
        return True
    except Exception as e:
        print(f"[ERROR] Error autorizando chat: {e}")
        return False

def auth_required(func):
    """Decorador para verificar autorización en grupos"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # En chats privados, permitir siempre
        if update.effective_chat.type == 'private':
            return await func(update, context)
        
        # En grupos, verificar autorización
        chat_id = update.effective_chat.id
        if not is_chat_authorized(chat_id):
            await update.message.reply_text(
                "❌ **Este grupo no está autorizado**\n\n"
                "📝 Un administrador debe usar `/solicitar` para pedir autorización",
                parse_mode='Markdown'
            )
            return
        
        return await func(update, context)
    
    return wrapper

# ========== SISTEMA DE SOLICITUDES ==========

def save_authorization_request(chat_id, chat_title, user_id, username):
    """Guarda solicitud de autorización en BD"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO authorization_requests 
        (chat_id, chat_title, requester_id, requester_username, request_date, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    ''', (chat_id, chat_title, user_id, username, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def is_authorization_pending(chat_id):
    """Verifica si hay solicitud pendiente"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM authorization_requests WHERE chat_id = ? AND status = 'pending'", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

# ========== COMANDOS DE AUTORIZACIÓN ==========

async def cmd_solicitar_autorizacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    ADMIN_BOT_ID = 5548909327  # 👈 TU ID REAL
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

async def cmd_aprobar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para aprobar solicitudes (solo admin bot)"""
    ADMIN_BOT_ID = 5548909327  # 👈 TU ID REAL
    
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
    if authorize_chat(chat_id, chat_title, ADMIN_BOT_ID):
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
            f"🎬 El grupo ya puede usar el bot",
            parse_mode='Markdown'
        )
        
    else:
        await update.message.reply_text("❌ Error al autorizar el grupo")
    
    conn.close()

async def cmd_ver_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver todas las solicitudes pendientes (solo admin bot)"""
    ADMIN_BOT_ID = 5548909327  # 👈 TU ID REAL
    
    if update.effective_user.id != ADMIN_BOT_ID:
        return
    
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
        try:
            fecha_formatted = datetime.fromisoformat(fecha).strftime("%d/%m %H:%M")
        except:
            fecha_formatted = fecha
        
        mensaje += (
            f"{i}. **{chat_title}**\n"
            f"   🆔 `{chat_id}`\n"
            f"   👤 @{username or 'sin username'}\n"
            f"   📅 {fecha_formatted}\n"
            f"   ✅ `/aprobar {chat_id}`\n\n"
        )
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# ========== COMANDOS PRINCIPALES ==========

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    welcome_text = (
        "🎬 **¡Bienvenido a CINEGRAM Puntum Bot!** 🍿\n\n"
        "🏆 **Sistema de puntos cinematográfico**\n"
        "Comparte contenido sobre películas y gana puntos\n\n"
        "🏷️ **Hashtags disponibles:**\n"
        "• `#aporte` (+10 pts) - Enlaces, noticias, curiosidades\n"
        "• `#reseña` (+20 pts) - Tu opinión sobre una película\n"
        "• `#crítica` (+30 pts) - Análisis profundo\n"
        "• `#recomendación` (+15 pts) - Recomienda películas\n\n"
        "📊 **Comandos útiles:**\n"
        "• `/ranking` - Ver top usuarios\n"
        "• `/miperfil` - Tu estadísticas\n"
        "• `/reto` - Reto diario\n"
        "• `/help` - Ayuda completa\n\n"
        "🍿 **¡Que comience la diversión cinematográfica!**"
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    help_text = (
        "🎬 **CINEGRAM Puntum Bot - Guía Completa** 🍿\n\n"
        "**🏷️ HASHTAGS Y PUNTOS:**\n"
        "• `#aporte` (+10) - Enlaces, noticias, curiosidades\n"
        "• `#reseña` (+20) - Tu opinión sobre películas\n"
        "• `#crítica` (+30) - Análisis cinematográfico\n"
        "• `#recomendación` (+15) - Recomienda films\n\n"
        "**📊 COMANDOS:**\n"
        "• `/ranking` - Top 10 usuarios\n"
        "• `/miperfil` - Tus estadísticas completas\n"
        "• `/reto` - Reto diario (+50 pts)\n"
        "• `/mirank` - Tu posición en ranking\n\n"
        "**🏆 NIVELES:**\n"
        "• Novato Cinéfilo (0+ pts)\n"
        "• Aficionado (100+ pts)\n"
        "• Crítico Amateur (250+ pts)\n"
        "• Experto Cinematográfico (500+ pts)\n"
        "• Maestro del Séptimo Arte (1000+ pts)\n\n"
        "**💡 CONSEJOS:**\n"
        "✓ Combina texto + hashtag para más puntos\n"
        "✓ Participa en retos diarios\n"
        "✓ Contenido original = más engagement\n\n"
        "🍿 **¡Disfruta compartiendo tu pasión por el cine!**"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ranking"""
    try:
        top_users = get_top10()
        
        if not top_users:
            await update.message.reply_text("📊 Aún no hay usuarios en el ranking")
            return
        
        ranking_text = "🏆 **TOP 10 CINÉFILOS** 🍿\n\n"
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, (username, points, level) in enumerate(top_users):
            medal = medals[i] if i < len(medals) else f"{i+1}️⃣"
            level_names = {
                1: "🎬 Novato",
                2: "🍿 Aficionado", 
                3: "🎭 Crítico",
                4: "🏆 Experto",
                5: "👑 Maestro"
            }
            level_name = level_names.get(level, "🎬 Novato")
            
            ranking_text += f"{medal} **{username}** - {points} pts ({level_name})\n"
        
        ranking_text += f"\n📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        await update.message.reply_text(ranking_text, parse_mode='Markdown')
        
    except Exception as e:
        print(f"[ERROR] cmd_ranking: {e}")
        await update.message.reply_text("❌ Error al obtener ranking")

async def cmd_miperfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /miperfil"""
    user_id = update.effective_user.id
    
    try:
        stats = get_user_stats(user_id)
        
        if not stats:
            await update.message.reply_text(
                "🎬 **¡Aún no tienes actividad!**\n\n"
                "Usa hashtags como `#aporte` o `#reseña` para comenzar a ganar puntos"
            )
            return
        
        # Calcular progreso al siguiente nivel
        progress_bar = ""
        if stats['points_to_next'] > 0:
            current_level_min = stats['points'] - stats['points_to_next']
            next_level_points = stats['points'] + stats['points_to_next']
            progress = (stats['points'] - current_level_min) / (next_level_points - current_level_min)
            filled = int(progress * 10)
            progress_bar = "▓" * filled + "░" * (10 - filled)
        else:
            progress_bar = "▓" * 10  # Nivel máximo
        
        # Hashtags más usados
        top_hashtags = sorted(stats['hashtag_counts'].items(), key=lambda x: x[1], reverse=True)[:3]
        hashtags_text = ""
        for hashtag, count in top_hashtags:
            hashtags_text += f"• {hashtag}: {count} veces\n"
        
        profile_text = (
            f"👤 **PERFIL DE {stats['username'].upper()}**\n\n"
            f"🏆 **Puntos totales:** {stats['points']}\n"
            f"📊 **Contribuciones:** {stats['count']}\n"
            f"🎭 **Nivel:** {stats['level_name']}\n"
            f"📈 **Progreso:** [{progress_bar}]\n"
        )
        
        if stats['points_to_next'] > 0:
            profile_text += f"🎯 **Para siguiente nivel:** {stats['points_to_next']} pts\n\n"
        else:
            profile_text += f"👑 **¡Nivel máximo alcanzado!**\n\n"
        
        profile_text += (
            f"**🏷️ Hashtags favoritos:**\n{hashtags_text}\n"
            f"📅 **Miembro desde:** {stats['member_since'][:10]}\n"
            f"🗓️ **Días activos:** {len(stats['active_days'])}\n"
            f"🎯 **Retos semanales:** {stats['daily_challenges_week']}/7"
        )
        
        await update.message.reply_text(profile_text, parse_mode='Markdown')
        
    except Exception as e:
        print(f"[ERROR] cmd_miperfil: {e}")
        await update.message.reply_text("❌ Error al obtener perfil")

async def cmd_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /reto - reto diario"""
    retos = [
        "🎭 Comparte una película que te hizo llorar",
        "🍿 Recomienda una película perfecta para palomitas",
        "🎬 Menciona un director que admires y por qué",
        "🏆 ¿Cuál fue la mejor película del año pasado?",
        "🎪 Comparte una película que pocos conocen",
        "🎨 Habla sobre una película con increíble cinematografía",
        "🎵 Menciona una película con banda sonora memorable",
        "😱 Recomienda una película de terror que realmente asuste",
        "😂 ¿Cuál es la comedia que más te ha hecho reír?",
        "🌟 Comparte tu actor/actriz favorito/a y una película suya"
    ]
    
    # Usar el día del año para consistencia
    import datetime
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    reto_hoy = retos[day_of_year % len(retos)]
    
    reto_text = (
        f"🎯 **RETO DIARIO - {datetime.datetime.now().strftime('%d/%m/%Y')}**\n\n"
        f"{reto_hoy}\n\n"
        f"💡 **¿Cómo participar?**\n"
        f"Responde con tu contenido + cualquier hashtag\n"
        f"¡Los retos dan puntos extra! 🏆\n\n"
        f"🏷️ Hashtags: `#aporte` `#reseña` `#crítica` `#recomendación`"
    )
    
    await update.message.reply_text(reto_text, parse_mode='Markdown')

async def handle_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes con hashtags"""
    try:
        message_text = update.message.text.lower()
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or "Usuario"
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        
        # Detectar hashtags y asignar puntos
        points_awarded = 0
        hashtags_found = []
        
        hashtag_points = {
            '#aporte': 10,
            '#reseña': 20,
            '#crítica': 30,
            '#recomendación': 15
        }
        
        # Buscar hashtags válidos
        for hashtag, points in hashtag_points.items():
            if hashtag in message_text:
                points_awarded += points
                hashtags_found.append(hashtag)
        
        if points_awarded > 0:
            # Bonus por longitud del mensaje (contenido de calidad)
            if len(message_text) > 100:
                points_awarded += 5
                
            # Registrar puntos en la base de datos
            for hashtag in hashtags_found:
                result = add_points(
                    user_id=user_id,
                    username=username,
                    points=hashtag_points[hashtag],
                    hashtag=hashtag,
                    message_text=message_text,
                    chat_id=chat_id,
                    message_id=message_id,
                    context=context
                )
            
            # Responder con confirmación
            response = f"🎬 **¡Puntos ganados!** 🍿\n\n"
            response += f"👤 **{username}**\n"
            response += f"🏷️ **Hashtags:** {', '.join(hashtags_found)}\n"
            response += f"🏆 **Puntos:** +{points_awarded}\n\n"
            
            if len(message_text) > 100:
                response += f"💡 **Bonus contenido:** +5 pts\n\n"
            
            response += f"📊 Usa `/miperfil` para ver tus estadísticas"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
            print(f"[POINTS] {username} ganó {points_awarded} puntos en chat {chat_id}")
        
    except Exception as e:
        print(f"[ERROR] handle_hashtags: {e}")

# ========== CONFIGURACIÓN Y INICIALIZACIÓN ==========

async def post_init(application):
    """Configurar comandos del bot"""
    commands = [
        BotCommand("start", "Iniciar bot y ver bienvenida"),
        BotCommand("help", "Ayuda y guía completa"),
        BotCommand("ranking", "Ver top 10 usuarios"),
        BotCommand("miperfil", "Ver mi perfil y estadísticas"),
        BotCommand("reto", "Ver reto diario"),
        BotCommand("solicitar", "Solicitar autorización (solo grupos)"),
    ]
    
    await application.bot.set_my_commands(commands)
    print("[INFO] ✅ Comandos del bot configurados")

def main():
    """Función principal"""
    # Verificar token
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("[ERROR] BOT_TOKEN no encontrado en variables de entorno")
        return
    
    print(f"[INFO] 🤖 Iniciando bot...")
    print(f"[INFO] 🔑 Token configurado: {token[:10]}...")
    
    # Crear tablas
    create_tables()  # De db.py
    create_auth_tables()  # Nuevas tablas de autorización
    
    # Crear aplicación
    app = ApplicationBuilder().token(token).post_init(post_init).build()
    
    # ========== COMANDOS DE AUTORIZACIÓN ==========
    app.add_handler(CommandHandler("solicitar", cmd_solicitar_autorizacion))
    app.add_handler(CommandHandler("aprobar", cmd_aprobar_grupo))
    app.add_handler(CommandHandler("solicitudes", cmd_ver_solicitudes))
    
    # ========== COMANDOS PRINCIPALES (CON AUTORIZACIÓN) ==========
    app.add_handler(CommandHandler("start", auth_required(cmd_start)))
    app.add_handler(CommandHandler("help", auth_required(cmd_help)))
    app.add_handler(CommandHandler("ranking", auth_required(cmd_ranking)))
    app.add_handler(CommandHandler("miperfil", auth_required(cmd_miperfil)))
    app.add_handler(CommandHandler("reto", auth_required(cmd_reto)))
    
    # ========== HANDLERS DE MENSAJES ==========
    hashtag_filter = filters.TEXT & ~filters.COMMAND & filters.Regex(r'#\w+')
    app.add_handler(MessageHandler(hashtag_filter, auth_required(handle_hashtags)))
    
    print("[INFO] ✅ Handlers configurados")
    
    # Iniciar polling para desarrollo local
    if os.environ.get("DEVELOPMENT"):
        print("[INFO] 🔄 Modo desarrollo - usando polling")
        app.run_polling()
    else:
        # Iniciar webhook para producción (Render)
        print("[INFO] 🌐 Modo producción - usando webhook")
        
        # Configurar webhook
        webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL', '')}/webhook"
        
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8000)),
            url_path="/webhook",
            webhook_url=webhook_url
        )

if __name__ == "__main__":
    main()
