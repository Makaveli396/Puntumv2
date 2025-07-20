from telegram import Update
from telegram.ext import ContextTypes
from db import get_user_stats, get_top10, add_points
import random

# Hashtags válidos para el sistema de puntos
VALID_HASHTAGS = {
    '#cinefilo': 5,
    '#pelicula': 3,
    '#critica': 4,
    '#actor': 2,
    '#director': 3,
    '#genero': 2,
    '#oscar': 5,
    '#festival': 4,
    '#cine': 3,
    '#serie': 3,
    '#documental': 4,
    '#animacion': 3,
    '#clasico': 4,
    '#independiente': 5
}

# Retos diarios
DAILY_CHALLENGES = [
    "🎬 Comparte tu película favorita de ciencia ficción",
    "🎭 Menciona un actor que te haya sorprendido en su último papel",
    "📽️ ¿Cuál fue la última película que viste en el cine?",
    "🏆 Nombra una película que mereció más reconocimiento",
    "📚 Comparte una adaptación cinematográfica que superó al libro",
    "🎨 Menciona un director con un estilo visual único",
    "🎵 ¿Qué película tiene tu banda sonora favorita?",
    "💔 Comparte una película que te hizo llorar",
    "😱 Menciona el mejor thriller que hayas visto",
    "🤣 ¿Cuál es tu comedia favorita?"
]

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de bienvenida"""
    user = update.effective_user
    chat = update.effective_chat
    
    welcome_message = f"""
🎬 **¡Bienvenido al Bot Cinéfilo!** 🍿

¡Hola {user.mention_html()}! 👋

**¿Qué puedes hacer aquí?**
🎯 Ganar puntos usando hashtags cinéfilos
🎮 Jugar trivia y juegos de películas
📊 Ver rankings y estadísticas
🏆 Completar retos diarios y semanales

**Comandos disponibles:**
/help - Guía completa
/ranking - Ver top 10
/miperfil - Tus estadísticas
/reto - Reto diario

**Juegos:**
/cinematrivia - Trivia de películas
/adivinapelicula - Adivina por pistas
/emojipelicula - Adivina por emojis

¡Comienza usando hashtags como #cinefilo #pelicula #critica!
    """
    
    await update.message.reply_text(
        welcome_message, 
        parse_mode='HTML',
        disable_web_page_preview=True
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de ayuda completa"""
    help_text = """
🎬 **GUÍA COMPLETA DEL BOT CINÉFILO**

**📊 SISTEMA DE PUNTOS**
Gana puntos usando hashtags en tus mensajes:
• #cinefilo - 5 pts
• #oscar #festival - 5 pts  
• #critica #documental - 4 pts
• #pelicula #director #cine #serie - 3 pts
• #actor #genero - 2 pts

**🎮 JUEGOS DISPONIBLES**
/cinematrivia - Trivia con opciones múltiples
/adivinapelicula - Adivina película por pistas
/emojipelicula - Adivina película por emojis
/pista - Pedir ayuda en juego activo
/rendirse - Abandonar juego actual

**📈 COMANDOS DE INFORMACIÓN**
/ranking - Top 10 usuarios globales
/miperfil - Tus estadísticas personales
/estadisticasjuegos - Tus stats de juegos
/topjugadores - Ranking de juegos

**🏆 SISTEMA DE NIVELES**
1️⃣ Novato Cinéfilo (0-99 pts)
2️⃣ Aficionado (100-249 pts)
3️⃣ Crítico Amateur (250-499 pts)
4️⃣ Experto Cinematográfico (500-999 pts)
5️⃣ Maestro del Séptimo Arte (1000+ pts)

**🎯 RETOS**
/reto - Ver reto diario (bonus extra)

¡Diviértete compartiendo tu pasión por el cine! 🍿
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cmd_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar ranking de usuarios"""
    top_users = get_top10()
    
    if not top_users:
        await update.message.reply_text("📊 Aún no hay usuarios en el ranking.")
        return
    
    ranking_text = "🏆 **TOP 10 CINÉFILOS** 🎬\n\n"
    
    medals = ["🥇", "🥈", "🥉"] + ["📍"] * 7
    
    for i, (username, points, level) in enumerate(top_users, 1):
        medal = medals[i-1] if i <= len(medals) else "📍"
        level_names = {
            1: "Novato", 2: "Aficionado", 3: "Crítico",
            4: "Experto", 5: "Maestro"
        }
        level_name = level_names.get(level, "Novato")
        
        ranking_text += f"{medal} **{i}.** {username}\n"
        ranking_text += f"    💎 {points} puntos - {level_name}\n\n"
    
    await update.message.reply_text(ranking_text, parse_mode='Markdown')

async def cmd_miperfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar perfil del usuario"""
    user = update.effective_user
    stats = get_user_stats(user.id)
    
    if not stats:
        await update.message.reply_text(
            "📊 Aún no tienes estadísticas.\n"
            "¡Comienza usando hashtags como #cinefilo #pelicula!"
        )
        return
    
    # Emojis de nivel
    level_emojis = {1: "🌱", 2: "🎭", 3: "🎬", 4: "🏆", 5: "👑"}
    level_emoji = level_emojis.get(stats['level'], "🌱")
    
    profile_text = f"""
{level_emoji} **PERFIL DE {stats['username'].upper()}**

📊 **Estadísticas Generales:**
💎 Puntos totales: **{stats['points']}**
📝 Contribuciones: **{stats['count']}**
🎯 Nivel: **{stats['level']} - {stats['level_name']}**

📈 **Progreso:**
"""
    
    if stats['points_to_next'] > 0:
        profile_text += f"⬆️ Faltan **{stats['points_to_next']}** puntos para subir de nivel\n"
    else:
        profile_text += "🏆 ¡Nivel máximo alcanzado!\n"
    
    profile_text += f"\n👤 **Miembro desde:** {stats['member_since'][:10]}\n"
    profile_text += f"📅 **Días activos:** {len(stats['active_days'])}\n"
    
    # Hashtags favoritos
    if stats['hashtag_counts']:
        top_hashtags = sorted(stats['hashtag_counts'].items(), 
                            key=lambda x: x[1], reverse=True)[:3]
        profile_text += f"\n🏷️ **Hashtags favoritos:**\n"
        for hashtag, count in top_hashtags:
            if hashtag and hashtag != '(reto_diario)':
                profile_text += f"   • {hashtag}: {count} veces\n"
    
    await update.message.reply_text(profile_text, parse_mode='Markdown')

async def cmd_reto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar reto diario"""
    import datetime
    
    # Usar la fecha para generar un reto consistente cada día
    today = datetime.date.today()
    random.seed(today.toordinal())
    daily_challenge = random.choice(DAILY_CHALLENGES)
    
    reto_text = f"""
🎯 **RETO DIARIO** 📅 {today.strftime('%d/%m/%Y')}

{daily_challenge}

**💡 Cómo participar:**
1️⃣ Responde al reto en un mensaje
2️⃣ Incluye hashtags relevantes (#cinefilo #pelicula etc.)
3️⃣ ¡Ganarás puntos bonus por participar!

**🏆 Bonus extra** si tu respuesta incluye:
• Datos curiosos o análisis profundo
• Recomendaciones para otros cinéfilos
• Hashtags específicos (#director #genero #oscar)

¡Comparte tu pasión por el cine! 🍿
    """
    
    await update.message.reply_text(reto_text, parse_mode='Markdown')

async def handle_hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes con hashtags cinéfilos"""
    message_text = update.message.text
    user = update.effective_user
    chat = update.effective_chat
    
    # Buscar hashtags válidos en el mensaje
    found_hashtags = []
    total_points = 0
    
    for hashtag, points in VALID_HASHTAGS.items():
        if hashtag in message_text.lower():
            found_hashtags.append((hashtag, points))
            total_points += points
    
    if not found_hashtags:
        return  # No hay hashtags válidos
    
    # Bonus por mensaje largo y detallado
    if len(message_text) > 100:
        total_points += 2
        bonus_text = " (+2 bonus por mensaje detallado)"
    else:
        bonus_text = ""
    
    # Agregar puntos al usuario
    primary_hashtag = found_hashtags[0][0]  # Usar el primer hashtag encontrado
    add_points(
        user_id=user.id,
        username=user.username or user.first_name,
        points=total_points,
        hashtag=primary_hashtag,
        message_text=message_text[:100],
        chat_id=chat.id,
        message_id=update.message.message_id,
        context=context
    )
    
    # Crear respuesta
    hashtags_list = ", ".join([h[0] for h in found_hashtags])
    
    response = f"""
✅ **¡Puntos ganados!** 🎬

👤 {user.mention_html()}
🏷️ Hashtags: {hashtags_list}
💎 **+{total_points} puntos**{bonus_text}

¡Sigue compartiendo tu pasión por el cine! 🍿
    """
    
    await update.message.reply_text(
        response, 
        parse_mode='HTML',
        reply_to_message_id=update.message.message_id
    )
