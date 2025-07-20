import sqlite3
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from db import get_connection

# Configuración - ID del administrador principal
ADMIN_USER_ID = 5548909327  # Cambiar por tu user_id de Telegram

def create_auth_tables():
    """Crear tablas para el sistema de autorización"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorized_chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            authorized_by INTEGER,
            authorized_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            chat_title TEXT,
            requested_by INTEGER,
            requester_username TEXT,
            requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    conn.commit()
    conn.close()
    print("[INFO] ✅ Tablas de autorización creadas")

def is_chat_authorized(chat_id: int) -> bool:
    """Verificar si un chat está autorizado"""
    # Permitir chats privados siempre
    if chat_id > 0:
        return True
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM authorized_chats WHERE chat_id = ? AND status = 'active'",
        (chat_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    return bool(result)

def authorize_chat(chat_id: int, chat_title: str, authorized_by: int):
    """Autorizar un chat"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO authorized_chats 
        (chat_id, chat_title, authorized_by, authorized_at, status)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'active')
    """, (chat_id, chat_title, authorized_by))
    
    # Marcar solicitud como aprobada
    cursor.execute("""
        UPDATE auth_requests 
        SET status = 'approved' 
        WHERE chat_id = ? AND status = 'pending'
    """, (chat_id,))
    
    conn.commit()
    conn.close()

def auth_required(func):
    """Decorador para requerir autorización en comandos"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        if not is_chat_authorized(chat_id):
            if chat_id < 0:  # Es un grupo
                await update.message.reply_text(
                    "❌ Este grupo no está autorizado para usar el bot.\n"
                    "📝 Usa /solicitar para pedir autorización."
                )
                return
            else:  # Chat privado - siempre permitido
                pass
        
        return await func(update, context)
    return wrapper

async def cmd_solicitar_autorizacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicitar autorización para un grupo"""
    chat = update.effective_chat
    user = update.effective_user
    
    # Solo funciona en grupos
    if chat.type == 'private':
        await update.message.reply_text(
            "ℹ️ Los chats privados no necesitan autorización.\n"
            "Este comando solo funciona en grupos."
        )
        return
    
    # Verificar si ya está autorizado
    if is_chat_authorized(chat.id):
        await update.message.reply_text("✅ Este grupo ya está autorizado.")
        return
    
    # Verificar si ya hay una solicitud pendiente
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM auth_requests WHERE chat_id = ? AND status = 'pending'",
        (chat.id,)
    )
    if cursor.fetchone():
        conn.close()
        await update.message.reply_text(
            "⏳ Ya hay una solicitud pendiente para este grupo.\n"
            "Por favor espera a que sea revisada."
        )
        return
    
    # Crear nueva solicitud
    cursor.execute("""
        INSERT INTO auth_requests 
        (chat_id, chat_title, requested_by, requester_username)
        VALUES (?, ?, ?, ?)
    """, (chat.id, chat.title, user.id, user.username or user.first_name))
    
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        "✅ Solicitud de autorización enviada.\n"
        f"📋 Grupo: {chat.title}\n"
        f"👤 Solicitado por: {user.mention_html()}\n"
        "⏳ Espera a que un administrador la revise.",
        parse_mode='HTML'
    )

async def cmd_aprobar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aprobar un grupo (solo administradores)"""
    user = update.effective_user
    
    # Verificar si es administrador
    if ADMIN_USER_ID is None:
        await update.message.reply_text(
            "⚠️ No hay administrador configurado.\n"
            "Configura ADMIN_USER_ID en sistema_autorizacion.py"
        )
        return
    
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Solo los administradores pueden usar este comando.")
        return
    
    # Obtener ID del grupo a aprobar
    if not context.args:
        await update.message.reply_text(
            "📝 Uso: /aprobar <chat_id>\n"
            "Usa /solicitudes para ver IDs pendientes."
        )
        return
    
    try:
        chat_id_to_approve = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID de chat inválido.")
        return
    
    # Buscar la solicitud
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT chat_title, requester_username 
        FROM auth_requests 
        WHERE chat_id = ? AND status = 'pending'
    """, (chat_id_to_approve,))
    
    request = cursor.fetchone()
    if not request:
        conn.close()
        await update.message.reply_text("❌ No hay solicitud pendiente para ese chat.")
        return
    
    chat_title, requester = request
    
    # Aprobar el grupo
    authorize_chat(chat_id_to_approve, chat_title, user.id)
    conn.close()
    
    await update.message.reply_text(
        f"✅ Grupo aprobado exitosamente:\n"
        f"📋 {chat_title}\n"
        f"👤 Solicitado por: {requester}\n"
        f"🆔 Chat ID: {chat_id_to_approve}"
    )
    
    # Notificar al grupo (opcional)
    try:
        await context.bot.send_message(
            chat_id=chat_id_to_approve,
            text="🎉 ¡Su grupo ha sido autorizado!\n"
                 "Ya pueden usar todos los comandos del bot."
        )
    except Exception as e:
        print(f"[WARNING] No se pudo notificar al grupo {chat_id_to_approve}: {e}")

async def cmd_ver_solicitudes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver solicitudes pendientes (solo administradores)"""
    user = update.effective_user
    
    if ADMIN_USER_ID is None or user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Solo los administradores pueden usar este comando.")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT chat_id, chat_title, requester_username, requested_at
        FROM auth_requests 
        WHERE status = 'pending'
        ORDER BY requested_at ASC
    """)
    
    requests = cursor.fetchall()
    conn.close()
    
    if not requests:
        await update.message.reply_text("✅ No hay solicitudes pendientes.")
        return
    
    message = "📋 **Solicitudes Pendientes:**\n\n"
    for chat_id, chat_title, requester, requested_at in requests:
        message += f"🆔 `{chat_id}`\n"
        message += f"📋 {chat_title}\n"
        message += f"👤 {requester}\n"
        message += f"📅 {requested_at}\n"
        message += f"▫️ Para aprobar: `/aprobar {chat_id}`\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# Función auxiliar para configurar administrador
def set_admin_user_id(admin_id: int):
    """Configurar ID del administrador principal"""
    global ADMIN_USER_ID
    ADMIN_USER_ID = admin_id
    print(f"[INFO] Administrador configurado: {admin_id}")
