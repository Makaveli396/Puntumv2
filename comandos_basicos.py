from telegram import Update
from telegram.ext import ContextTypes
from db import get_user_stats, get_top10, add_points
import random
import datetime
import logging
import re
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HASHTAGS UNIFICADOS - SIN REPETICIONES Y CON DETECCIÓN FLEXIBLE
VALID_HASHTAGS = {
    # Alto valor
    'critica': 10,         # Análisis profundo, mínimo 100 palabras  
    'reseña': 7,           # Reseña detallada, mínimo 50 palabras
    'resena': 7,           # Sin tilde
    'recomendacion': 5,    # Formato específico requerido
    
    # Participación media
    'debate': 4,
    'aporte': 3,
    'cinefilo': 3,
    'pelicula': 3,
    'cine': 3,
    'serie': 3,
    'director': 3,
    'oscar': 3,
    'festival': 3,
    'documental': 3,
    'animacion': 3,
    'clasico': 3,
    'independiente': 3,
    
    # Participación baja
    'actor': 2,
    'genero': 2,
    'pregunta': 2,
    'ranking': 2,
    'rankin': 2,           # Typo común
    
    # Mínimo
    'spoiler': 1
}

# Cache para control de spam
user_hashtag_cache = {}

def normalize_text(text):
    """Normaliza texto removiendo tildes y caracteres especiales"""
    import unicodedata
    # Remover tildes
    normalized = unicodedata.normalize('NFD', text)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return normalized.lower()

def find_hashtags_in_message(text):
    """Encuentra TODOS los hashtags válidos en el mensaje con detección flexible"""
    if not text:
        return []
    
    found_hashtags = []
    text_normalized = normalize_text(text)
    
    # Extraer todos los hashtags del texto
    hashtag_pattern = r'#(\w+)'
    hashtags_in_text = re.findall(hashtag_pattern, text_normalized)
    
    print(f"[DEBUG] Hashtags extraídos del texto: {hashtags_in_text}")
    
    # Verificar cada hashtag extraído contra nuestra lista válida
    for hashtag_word in hashtags_in_text:
        if hashtag_word in VALID_HASHTAGS:
            points = VALID_HASHTAGS[hashtag_word]
            found_hashtags.append((f"#{hashtag_word}", points))
            print(f"[DEBUG] ✅ Hashtag válido encontrado: #{hashtag_word} = {points} puntos")
        else:
            print(f"[DEBUG] ❌ Hashtag NO válido: #{hashtag_word}")
    
    # Eliminar duplicados manteniendo el orden
    unique_hashtags = []
    seen = set()
    for hashtag, points in found_hashtags:
        if hashtag not in seen:
            unique_hashtags.append((hashtag, points))
            seen.add(hashtag)
    
    print(f"[DEBUG] Hashtags únicos finales: {unique_hashtags}")
    return unique_hashtags

def is_spam(user_id, hashtag):
    """Detecta spam basado en frecuencia de hashtags por usuario"""
    current_time = time.time()
    
    if user_id not in user_hashtag_cache:
        user_hashtag_cache[user_id] = {}
    
    user_data = user_hashtag_cache[user_id]
    
    # Limpiar datos antiguos (más de 5 minutos)
    if "last_time" in user_data and current_time - user_data["last_time"] > 300:
        user_data.clear()
    
    # Contar uso del hashtag
    if hashtag in user_data:
        user_data[hashtag] = user_data.get(hashtag, 0) + 1
        if user_data[hashtag] > 3:  # Máximo 3 veces en 5 minutos
            return True
    else:
        user_data[hashtag] = 1
    
    user_data["last_time"] = current_time
    return False

def count_words(text):
    """Cuenta palabras sin incluir hashtags"""
    if not text:
        return 0
    text_without_hashtags = re.sub(r'#\w+', '', text)
    return len(text_without_hashtags.split())

# Niveles del sistema
LEVEL_THRESHOLDS = {
    1: (0, 99, "Novato Cinéfilo", "🌱"),
    2: (100, 249, "Aficionado", "🎭"),
    3: (250, 499, "Crítico Amateur", "🎬"),
    4: (500, 999, "Experto Cinematográfico", "🏆"),
    5: (1000, float('inf'), "Maestro del Séptimo Arte", "👑")
}

# Retos diarios expandidos
DAILY_CHALLENGES = [
    "🎬 Comparte tu película favorita de ciencia ficción y explica por qué",
    "🎭 Menciona un actor que te haya sorprendido en su último papel",
    "📽️ ¿Cuál fue la última película que viste en el cine? ¿La recomendarías?",
    "🏆 Nombra una película que mereció más reconocimiento en los premios",
    "📚 Comparte una adaptación cinematográfica que superó al libro original",
    "🎨 Menciona un director con un estilo visual único y describe su técnica",
    "🎵 ¿Qué película tiene tu banda sonora favorita? Comparte una canción",
    "💔 Comparte una película que te hizo llorar y explica la escena",
    "😱 Menciona el mejor thriller que hayas visto este año",
    "🤣 ¿Cuál es tu comedia favorita y tu escena más divertida?",
    "🌍 Recomienda una película internacional que pocos conozcan",
    "🎪 Habla sobre tu película de superhéroes favorita",
    "🏠 ¿Cuál es la mejor película para ver en casa con la familia?",
    "🎨 Menciona una película con una cinematografía excepcional",
    "🎬 ¿Qué película clásica recomendarías a los jóvenes de hoy?"
]

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de bienvenida mejorado"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Verificar si es grupo o chat privado
    chat_type = "grupo" if chat.type in ['group', 'supergroup'] else "chat privado"
    
    welcome_message = f"""🎬 **¡Bienvenido al Bot Cinéfilo!** 🍿

¡Hola {user.mention_html()}! 👋

Estás en un {chat_type} dedicado al séptimo arte.

**🎯 ¿Qué puedes hacer aquí?**
• Ganar puntos usando hashtags cinéfilos
• Jugar trivia y juegos de películas  
• Ver rankings y estadísticas
• Completar retos diarios y semanales
• Participar en debates cinematográficos

**📋 Comandos principales:**
• `/help` - Guía completa del bot
• `/ranking` - Ver top 10 usuarios
• `/miperfil` - Tus estadísticas personales
• `/reto` - Reto diario actual

**🎮 Juegos disponibles:**
• `/cinematrivia` - Trivia de películas
• `/adivinapelicula` - Adivina por pistas
• `/emojipelicula` - Adivina por emojis

**💡 ¡Primer consejo!**
Comienza usando hashtags como **#cinefilo #pelicula #critica** 
¡Cada hashtag te da puntos diferentes!

¿Listo para convertirte en un maestro del séptimo arte? 🏆"""
    
    try:
        await update.message.reply_text(
            welcome_message, 
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        logger.info(f"Usuario {user.id} inició el bot en {chat_type}")
    except Exception as e:
        logger.error(f"Error en cmd_start: {e}")
        await update.message.reply_text("¡Bienvenido al Bot Cinéfilo! Usa /help para más información.")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de ayuda completa - SINCRONIZADO CON FUNCIONES"""
    help_text = """🎬 *GUÍA COMPLETA DEL BOT CINÉFILO*

📊 *SISTEMA DE PUNTOS*
Gana puntos usando hashtags en tus mensajes:

*Hashtags de Alto Valor:*
• *\\#critica* \\- 10 pts \\(análisis profundo\\)
• *\\#reseña* \\- 7 pts \\(reseña detallada\\)  
• *\\#recomendacion* \\- 5 pts \\(incluye datos específicos\\)

*Hashtags de Participación:*
• *\\#debate* \\- 4 pts \\(discusión cinematográfica\\)
• *\\#aporte* \\- 3 pts \\(contribución al grupo\\)
• *\\#cinefilo* \\- 3 pts \\(pasión por el cine\\)
• *\\#pelicula*, *\\#cine*, *\\#serie* \\- 3 pts
• *\\#director*, *\\#oscar*, *\\#festival* \\- 3 pts
• *\\#documental*, *\\#animacion*, *\\#clasico* \\- 3 pts
• *\\#independiente* \\- 3 pts
• *\\#actor*, *\\#genero*, *\\#pregunta* \\- 2 pts
• *\\#ranking* \\- 2 pts
• *\\#spoiler* \\- 1 pt \\(marca contenido sensible\\)

🎮 *JUEGOS \\(Próximamente\\)*
• `/cinematrivia` \\- Trivia con opciones múltiples
• `/adivinapelicula` \\- Adivina película por pistas
• `/emojipelicula` \\- Adivina por emojis

📈 *COMANDOS DISPONIBLES*
• `/start` \\- Iniciar y conocer el bot
• `/help` \\- Esta guía completa
• `/ranking` \\- Top 10 usuarios del grupo
• `/miperfil` \\- Tus estadísticas personales
• `/reto` \\- Ver reto diario actual

🎯 *SISTEMA DE BONIFICACIONES*
• *\\+2 pts* por mensajes detallados \\(150\\+ caracteres\\)
• *\\+1 pt* por participar en retos diarios
• *Validaciones especiales:*
  \\- \\#critica requiere análisis desarrollado
  \\- \\#reseña necesita descripción detallada

🏆 *SISTEMA DE NIVELES*
1️⃣ *Novato Cinéfilo* \\(0\\-99 pts\\) 🌱
2️⃣ *Aficionado* \\(100\\-249 pts\\) 🎭
3️⃣ *Crítico Amateur* \\(250\\-499 pts\\) 🎬
4️⃣ *Experto Cinematográfico* \\(500\\-999 pts\\) 🏆
5️⃣ *Maestro del Séptimo Arte* \\(1000\\+ pts\\) 👑

💡 *CONSEJOS PARA MAXIMIZAR PUNTOS*
• Combina múltiples hashtags únicos en un mensaje
• Escribe análisis detallados para \\#critica
• Participa en el reto diario \\(/reto\\)
• Contribuye con \\#aporte y \\#debate
• Evita repetir el mismo hashtag muy seguido

📋 *CÓMO USAR EL BOT*
1\\. Escribe mensajes o aportes sobre cine con hashtags
2\\. El bot detecta automáticamente los hashtags válidos
3\\. Recibes puntos y feedback inmediato
4\\. Consulta tu progreso con /miperfil
5\\. Compite en el /ranking con otros usuarios

⚠️ *NORMAS DEL GRUPO*
• Solo contenido relacionado con cine y series
• Respeto en debates y discusiones  
• Marca spoilers con \\#spoiler
• No spam de hashtags repetidos

¡Diviértete compartiendo tu pasión por el cine\\! 🍿"""
    
    try:
        await update.message.reply_text(help_text, parse_mode='MarkdownV2')
        logger.info(f"Usuario {update.effective_user.id} solicitó ayuda")
    except Exception as e:
        logger.error(f"Error en cmd_help con MarkdownV2: {e}")
        # Fallback sin formato
        simple_help = """🎬 GUÍA DEL BOT CINÉFILO

📊 SISTEMA DE PUNTOS:
• #critica - 10 pts (análisis profundo)
• #reseña - 7 pts (reseña detallada)  
• #recomendacion - 5 pts
• #debate - 4 pts
• #aporte, #cinefilo, #pelicula - 3 pts
• #pregunta, #ranking - 2 pts
• #spoiler - 1 pt

🎮 JUEGOS: /cinematrivia, /adivinapelicula, /emojipelicula
📈 INFO: /ranking, /miperfil, /reto
🏆 NIVELES: 1-Novato, 2-Aficionado, 3-Crítico, 4-Experto, 5-Maestro

¡Usa hashtags en tus mensajes para ganar puntos! 🍿"""
        await update.message.reply_text(simple_help)

async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar ranking de usuarios mejorado"""
    try:
        top_users = get_top10()
        
        if not top_users:
            await update.message.reply_text(
                "📊 Aún no hay usuarios en el ranking.\n"
                "¡Sé el primero en ganar puntos usando hashtags! 🎬"
            )
            return
        
        ranking_text = "🏆 *TOP 10 CINÉFILOS* 🎬\n\n"
        
        medals = ["🥇", "🥈", "🥉"] + ["📍"] * 7
        
        for i, user_data in enumerate(top_users, 1):
            # Manejar diferentes formatos de datos
            if len(user_data) >= 3:
                username, points, level = user_data[0], user_data[1], user_data[2]
            else:
                username, points = user_data[0], user_data[1]
                level = calculate_level(points)
            
            medal = medals[i-1] if i <= len(medals) else "📍"
            level_info = LEVEL_THRESHOLDS.get(level, (0, 0, "Novato", "🌱"))
            level_name, level_emoji = level_info[2], level_info[3]
            
            ranking_text += f"{medal} *{i}\\.* {username}\n"
            ranking_text += f"    {level_emoji} {points} puntos \\- {level_name}\n\n"
        
        await update.message.reply_text(ranking_text, parse_mode='MarkdownV2')
        logger.info(f"Usuario {update.effective_user.id} consultó ranking")
        
    except Exception as e:
        logger.error(f"Error en cmd_ranking: {e}")
        await update.message.reply_text("❌ Error al obtener el ranking. Intenta más tarde.")

def calculate_level(points):
    """Calcular nivel basado en puntos"""
    for level, (min_pts, max_pts, _, _) in LEVEL_THRESHOLDS.items():
        if min_pts <= points <= max_pts:
            return level
    return 1

async def cmd_miperfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar perfil del usuario mejorado"""
    user = update.effective_user
    
    try:
        stats = get_user_stats(user.id)
        
        if not stats:
            await update.message.reply_text(
                "📊 Aún no tienes estadísticas registradas.\n\n"
                "💡 *¿Cómo empezar a ganar puntos?*\n"
                "• Escribe mensajes con hashtags como #cinefilo #pelicula\n"
                "• Participa en debates con #debate\n"
                "• Comparte reseñas con #reseña\n"
                "• Haz críticas detalladas con #critica\n\n"
                "¡Tu primer mensaje con hashtag te dará tus primeros puntos! 🎬",
                parse_mode='MarkdownV2'
            )
            return
        
        level = stats.get('level', calculate_level(stats['points']))
        level_info = LEVEL_THRESHOLDS.get(level, (0, 0, "Novato", "🌱"))
        level_name, level_emoji = level_info[2], level_info[3]
        
        profile_text = f"""{level_emoji} *PERFIL DE {stats['username'].upper().replace('_', '\\_')}*

📊 *Estadísticas Generales:*
💎 Puntos totales: *{stats['points']}*
📝 Contribuciones: *{stats['count']}*
🎯 Nivel: *{level} \\- {level_name}*

📈 *Progreso:*"""
        
        # Calcular puntos para siguiente nivel
        next_level_info = LEVEL_THRESHOLDS.get(level + 1)
        if next_level_info and level < 5:
            points_needed = next_level_info[0] - stats['points']
            profile_text += f"\n⬆️ Faltan *{points_needed}* puntos para subir de nivel"
        else:
            profile_text += f"\n🏆 ¡Nivel máximo alcanzado\\!"
        
        # Información adicional si está disponible
        if 'member_since' in stats:
            profile_text += f"\n\n👤 *Miembro desde:* {stats['member_since'][:10]}"
        
        if 'active_days' in stats:
            profile_text += f"\n📅 *Días activos:* {len(stats['active_days'])}"
        
        # Hashtags favoritos
        if stats.get('hashtag_counts'):
            top_hashtags = sorted(stats['hashtag_counts'].items(), 
                                key=lambda x: x[1], reverse=True)[:3]
            profile_text += f"\n\n🏷️ *Hashtags favoritos:*"
            for hashtag, count in top_hashtags:
                if hashtag and hashtag != '(reto_diario)':
                    clean_hashtag = hashtag.replace('_', '\\_').replace('#', '\\#')
                    profile_text += f"\n   • {clean_hashtag}: {count} veces"
        
        await update.message.reply_text(profile_text, parse_mode='MarkdownV2')
        logger.info(f"Usuario {user.id} consultó su perfil")
        
    except Exception as e:
        logger.error(f"Error en cmd_miperfil: {e}")
        await update.message.reply_text("❌ Error al obtener tu perfil. Intenta más tarde.")

async def cmd_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar reto diario mejorado"""
    today = datetime.date.today()
    
    # Usar la fecha para generar un reto consistente cada día
    random.seed(today.toordinal())
    daily_challenge = random.choice(DAILY_CHALLENGES)
    
    # Hashtags sugeridos para el reto
    suggested_hashtags = random.sample([
        '#cinefilo', '#recomendacion', '#critica', 
        '#debate', '#aporte', '#pelicula'
    ], 3)
    
    reto_text = f"""🎯 *RETO DIARIO* 📅 {today.strftime('%d/%m/%Y')}

{daily_challenge}

💡 *Cómo participar:*
1️⃣ Responde al reto en un mensaje
2️⃣ Incluye hashtags relevantes
3️⃣ ¡Gana puntos automáticamente\\!

🏷️ *Hashtags sugeridos para hoy:*
{' '.join(suggested_hashtags)}

🏆 *Bonus extra si incluyes:*
• Datos curiosos o análisis detallado
• Recomendaciones para otros cinéfilos  
• Mensajes de 100\\+ palabras \\(\\+2 pts bonus\\)

⏰ *Nuevo reto disponible cada día a las 00:00*

¡Comparte tu pasión por el cine\\! 🍿"""
    
    try:
        await update.message.reply_text(reto_text, parse_mode='MarkdownV2')
        logger.info(f"Usuario {update.effective_user.id} consultó reto diario")
    except Exception as e:
        logger.error(f"Error en cmd_reto: {e}")
        # Fallback simple
        simple_text = f"🎯 RETO DIARIO - {today.strftime('%d/%m/%Y')}\n\n{daily_challenge}\n\n¡Responde usando hashtags cinéfilos para ganar puntos! 🍿"
        await update.message.reply_text(simple_text)

async def handle_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FUNCIÓN PRINCIPAL CORREGIDA - Detecta TODOS los hashtags válidos"""
    if not update.message or not update.message.text:
        return
    
    message_text = update.message.text
    user = update.effective_user
    chat = update.effective_chat
    
    print(f"[DEBUG] 🔍 Procesando mensaje de {user.username or user.first_name}")
    print(f"[DEBUG] 📝 Texto completo: {message_text}")
    print(f"[DEBUG] 🏷️ Chat ID: {chat.id}")
    
    # 🎯 NUEVA DETECCIÓN MEJORADA
    found_hashtags = find_hashtags_in_message(message_text)
    
    if not found_hashtags:
        print(f"[DEBUG] ❌ No se encontraron hashtags válidos en: {message_text}")
        return
    
    print(f"[DEBUG] ✅ Hashtags encontrados: {found_hashtags}")
    
    # Verificar spam y calcular puntos
    valid_hashtags = []
    total_points = 0
    warnings = []
    
    for hashtag, points in found_hashtags:
        hashtag_word = hashtag[1:]  # Remover el #
        
        # Verificar spam
        if is_spam(user.id, hashtag):
            warnings.append(f"⚠️ {hashtag}: Detectado spam. Usa hashtags con moderación.")
            print(f"[DEBUG] 🚫 Spam detectado para {hashtag}")
            continue
        
        # Validaciones especiales
        word_count = count_words(message_text)
        
        if hashtag_word == "critica" and word_count < 25:
            warnings.append(f"❌ {hashtag}: Necesitas análisis más profundo (mín. 100 palabras). Tienes ~{word_count*4} palabras.")
            points = max(1, points // 2)  # Reducir puntos pero dar algo
        elif hashtag_word in ["reseña", "resena"] and word_count < 15:
            warnings.append(f"❌ {hashtag}: Necesitas reseña más detallada (mín. 50 palabras). Tienes ~{word_count*4} palabras.")
            points = max(1, points // 2)  # Reducir puntos pero dar algo
        
        valid_hashtags.append((hashtag, points))
        total_points += points
        print(f"[DEBUG] ✅ {hashtag} = {points} puntos")
    
    if total_points <= 0:
        print(f"[DEBUG] ❌ Total de puntos = 0, no se procesará")
        return
    
    # Bonus por mensaje detallado
    bonus_text = ""
    if len(message_text) > 150:
        total_points += 2
        bonus_text = " (+2 bonus detalle)"
    
    print(f"[DEBUG] 💎 Total de puntos a otorgar: {total_points}")
    
    try:
        # Guardar en base de datos
        primary_hashtag = valid_hashtags[0][0] if valid_hashtags else "#aporte"
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=total_points,
            hashtag=primary_hashtag,
            message_text=message_text[:200],  # Guardar más texto para contexto
            chat_id=chat.id,
            message_id=update.message.message_id,
            context=context
        )
        
        print(f"[DEBUG] ✅ Puntos guardados en BD exitosamente")
        
        # Crear respuesta
        hashtags_list = ", ".join([h[0] for h, p in valid_hashtags])
        
        responses = [
            "¡Excelente aporte cinéfilo!",
            "¡Puntos ganados!",
            "¡Gran contribución al cine!",
            "¡Sigue así, cinéfilo!",
            "¡Fantástico análisis!",
            "¡Perfecto para el grupo!"
        ]
        
        random_response = random.choice(responses)
        
        response = f"""✅ **{random_response}** 🎬

👤 {user.mention_html()}
🏷️ {hashtags_list}  
💎 **+{total_points} puntos**{bonus_text}

🎭 ¡Sigue compartiendo tu pasión por el cine! 🍿"""
        
        # Agregar advertencias si las hay
        if warnings:
            response += f"\n\n⚠️ **Notas:**\n" + "\n".join(warnings)
        
        await update.message.reply_text(
            response, 
            parse_mode='HTML',
            reply_to_message_id=update.message.message_id
        )
        
        print(f"[DEBUG] ✅ Respuesta enviada correctamente")
        logger.info(f"Usuario {user.id} ganó {total_points} puntos con: {hashtags_list}")
        
    except Exception as e:
        logger.error(f"❌ ERROR en handle_hashtags: {e}")
        import traceback
        traceback.print_exc()
        
        # Respuesta de emergencia
        try:
            await update.message.reply_text(f"✅ ¡Puntos ganados! +{total_points} pts 🎬")
        except:
            print(f"[DEBUG] ❌ No se pudo enviar ni la respuesta de emergencia")

    print(f"[DEBUG] 🏁 handle_hashtags terminado para {user.username or user.first_name}")
