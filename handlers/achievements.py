#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

# ========== DEFINICIÓN DE INSIGNIAS ==========

ACHIEVEMENTS = {
    1: {
        "id": 1,
        "name": "🎬 Primer Paso",
        "description": "Tu primera contribución cinematográfica",
        "requirement": "first_contribution",
        "points_bonus": 25,
        "rarity": "common"
    },
    2: {
        "id": 2,
        "name": "🔥 Racha Caliente",
        "description": "5 días consecutivos participando",
        "requirement": "streak_5_days",
        "points_bonus": 100,
        "rarity": "rare"
    },
    3: {
        "id": 3,
        "name": "🎭 Crítico Incansable",
        "description": "20 reseñas escritas",
        "requirement": "20_reviews",
        "points_bonus": 150,
        "rarity": "rare"
    },
    4: {
        "id": 4,
        "name": "🎪 Explorador de Géneros",
        "description": "Mencionar 10 géneros diferentes",
        "requirement": "10_genres",
        "points_bonus": 200,
        "rarity": "epic"
    },
    5: {
        "id": 5,
        "name": "⚡ Velocista",
        "description": "10 contribuciones en un día",
        "requirement": "10_daily_contributions",
        "points_bonus": 75,
        "rarity": "uncommon"
    },
    6: {
        "id": 6,
        "name": "📚 Enciclopedia Viviente",
        "description": "100 contribuciones totales",
        "requirement": "100_contributions",
        "points_bonus": 300,
        "rarity": "legendary"
    },
    7: {
        "id": 7,
        "name": "🌟 Influencer Cinematográfico",
        "description": "Alcanzar nivel Maestro",
        "requirement": "max_level",
        "points_bonus": 500,
        "rarity": "legendary"
    }
}

GENRES_KEYWORDS = {
    'acción': ['accion', 'action', 'explosiones', 'peleas', 'lucha'],
    'terror': ['terror', 'horror', 'miedo', 'suspense', 'thriller'],
    'comedia': ['comedia', 'comedy', 'risa', 'humor', 'divertida'],
    'drama': ['drama', 'emocional', 'llorar', 'sentimientos'],
    'sci-fi': ['ciencia ficcion', 'sci-fi', 'scifi', 'futuro', 'espacio'],
    'romance': ['romance', 'amor', 'romantica', 'pareja'],
    'aventura': ['aventura', 'adventure', 'viaje', 'explorar'],
    'animacion': ['animacion', 'animation', 'pixar', 'disney'],
    'documental': ['documental', 'documentary', 'real', 'historia'],
    'musical': ['musical', 'musica', 'cantando', 'baile']
}

# ========== FUNCIONES DE BASE DE DATOS ==========

def create_achievements_tables():
    """Crear tablas para el sistema de logros"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # Tabla de logros desbloqueados por usuario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER,
            achievement_id INTEGER,
            unlocked_date TEXT DEFAULT CURRENT_TIMESTAMP,
            notified INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, achievement_id)
        )
    ''')
    
    # Tabla para rastrear géneros mencionados por usuario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_genres (
            user_id INTEGER,
            genre TEXT,
            first_mention_date TEXT DEFAULT CURRENT_TIMESTAMP,
            mention_count INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, genre)
        )
    ''')
    
    # Tabla para rastrear rachas de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_streaks (
            user_id INTEGER PRIMARY KEY,
            current_streak INTEGER DEFAULT 0,
            max_streak INTEGER DEFAULT 0,
            last_contribution_date TEXT DEFAULT CURRENT_DATE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[INFO] 🏆 Tablas de logros creadas/verificadas")

def unlock_achievement(user_id: int, achievement_id: int) -> bool:
    """Desbloquear un logro para un usuario"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
            (user_id, achievement_id)
        )
        
        # Verificar si realmente se insertó (no existía antes)
        if cursor.rowcount > 0:
            conn.commit()
            print(f"[ACHIEVEMENT] Usuario {user_id} desbloqueó logro {achievement_id}")
            return True
            
    except Exception as e:
        print(f"[ERROR] unlock_achievement: {e}")
    finally:
        conn.close()
    
    return False

def get_user_achievements(user_id: int) -> list:
    """Obtener logros desbloqueados por un usuario"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT achievement_id, unlocked_date FROM user_achievements WHERE user_id = ?",
        (user_id,)
    )
    
    achievements = cursor.fetchall()
    conn.close()
    
    return [(aid, date) for aid, date in achievements]

def update_user_streak(user_id: int):
    """Actualizar la racha de un usuario"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Obtener racha actual
    cursor.execute(
        "SELECT current_streak, max_streak, last_contribution_date FROM user_streaks WHERE user_id = ?",
        (user_id,)
    )
    
    result = cursor.fetchone()
    
    if result:
        current_streak, max_streak, last_date_str = result
        try:
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
        except:
            last_date = yesterday  # Fallback
        
        # Calcular nueva racha
        if last_date == yesterday:
            # Continúa la racha
            new_streak = current_streak + 1
        elif last_date == today:
            # Ya contribuyó hoy
            new_streak = current_streak
        else:
            # Se rompió la racha
            new_streak = 1
        
        new_max_streak = max(max_streak, new_streak)
        
        cursor.execute(
            "UPDATE user_streaks SET current_streak = ?, max_streak = ?, last_contribution_date = ? WHERE user_id = ?",
            (new_streak, new_max_streak, today.isoformat(), user_id)
        )
    else:
        # Primera vez
        cursor.execute(
            "INSERT INTO user_streaks (user_id, current_streak, max_streak, last_contribution_date) VALUES (?, 1, 1, ?)",
            (user_id, today.isoformat())
        )
        new_streak = 1
    
    conn.commit()
    conn.close()
    
    return new_streak

def detect_genres_in_message(message_text: str) -> list:
    """Detectar géneros cinematográficos en un mensaje"""
    message_lower = message_text.lower()
    found_genres = []
    
    for genre, keywords in GENRES_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                found_genres.append(genre)
                break  # Solo contar cada género una vez por mensaje
    
    return found_genres

def track_user_genres(user_id: int, genres: list):
    """Rastrear géneros mencionados por usuario"""
    if not genres:
        return 0
    
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    new_genres_count = 0
    
    for genre in genres:
        cursor.execute(
            "SELECT mention_count FROM user_genres WHERE user_id = ? AND genre = ?",
            (user_id, genre)
        )
        
        result = cursor.fetchone()
        
        if result:
            # Incrementar contador
            cursor.execute(
                "UPDATE user_genres SET mention_count = mention_count + 1 WHERE user_id = ? AND genre = ?",
                (user_id, genre)
            )
        else:
            # Nuevo género para este usuario
            cursor.execute(
                "INSERT INTO user_genres (user_id, genre) VALUES (?, ?)",
                (user_id, genre)
            )
            new_genres_count += 1
    
    conn.commit()
    conn.close()
    
    return new_genres_count

def get_user_genre_count(user_id: int) -> int:
    """Obtener cantidad de géneros únicos mencionados por usuario"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(DISTINCT genre) FROM user_genres WHERE user_id = ?",
        (user_id,)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else 0

# ========== VERIFICADOR DE LOGROS ==========

def check_achievements(user_id: int, username: str, context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_text: str = ""):
    """Verificar y desbloquear logros automáticamente"""
    try:
        from db import get_user_stats
        
        # Obtener estadísticas del usuario
        stats = get_user_stats(user_id)
        if not stats:
            return
        
        new_achievements = []
        
        # 1. PRIMER PASO
        if stats['count'] == 1 and not has_achievement(user_id, 1):
            if unlock_achievement(user_id, 1):
                new_achievements.append(1)
        
        # 2. RACHA CALIENTE (5 días)
        current_streak = update_user_streak(user_id)
        if current_streak >= 5 and not has_achievement(user_id, 2):
            if unlock_achievement(user_id, 2):
                new_achievements.append(2)
        
        # 3. CRÍTICO INCANSABLE (20 reseñas)
        review_count = stats['hashtag_counts'].get('#reseña', 0)
        if review_count >= 20 and not has_achievement(user_id, 3):
            if unlock_achievement(user_id, 3):
                new_achievements.append(3)
        
        # 4. EXPLORADOR DE GÉNEROS
        genres_in_message = detect_genres_in_message(message_text)
        track_user_genres(user_id, genres_in_message)
        
        total_genres = get_user_genre_count(user_id)
        if total_genres >= 10 and not has_achievement(user_id, 4):
            if unlock_achievement(user_id, 4):
                new_achievements.append(4)
        
        # 5. VELOCISTA (10 contribuciones en un día)
        today = datetime.now().date().isoformat()
        daily_count = count_daily_contributions(user_id, today)
        if daily_count >= 10 and not has_achievement(user_id, 5):
            if unlock_achievement(user_id, 5):
                new_achievements.append(5)
        
        # 6. ENCICLOPEDIA VIVIENTE (100 contribuciones)
        if stats['count'] >= 100 and not has_achievement(user_id, 6):
            if unlock_achievement(user_id, 6):
                new_achievements.append(6)
        
        # 7. INFLUENCER CINEMATOGRÁFICO (nivel máximo)
        if stats['level'] >= 5 and not has_achievement(user_id, 7):
            if unlock_achievement(user_id, 7):
                new_achievements.append(7)
        
        # Notificar nuevos logros
        if new_achievements:
            notify_achievements(context, chat_id, username, new_achievements)
    
    except Exception as e:
        print(f"[ERROR] check_achievements: {e}")

def has_achievement(user_id: int, achievement_id: int) -> bool:
    """Verificar si un usuario ya tiene un logro"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
        (user_id, achievement_id)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def count_daily_contributions(user_id: int, date: str) -> int:
    """Contar contribuciones de un usuario en un día específico"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(*) FROM points WHERE user_id = ? AND DATE(timestamp) = ?",
        (user_id, date)
    )
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else 0

async def notify_achievements(context: ContextTypes.DEFAULT_TYPE, chat_id: int, username: str, achievement_ids: list):
    """Notificar nuevos logros desbloqueados"""
    try:
        for achievement_id in achievement_ids:
            achievement = ACHIEVEMENTS.get(achievement_id)
            if not achievement:
                continue
            
            rarity_emojis = {
                "common": "⚪",
                "uncommon": "🟢",
                "rare": "🔵",
                "epic": "🟣",
                "legendary": "🟡"
            }
            
            rarity_emoji = rarity_emojis.get(achievement['rarity'], "⚪")
            
            message = (
                f"🎉 **¡LOGRO DESBLOQUEADO!** 🎉\n\n"
                f"{rarity_emoji} **{achievement['name']}**\n"
                f"📝 {achievement['description']}\n"
                f"👤 **{username}**\n"
                f"🏆 **Bonus:** +{achievement['points_bonus']} puntos\n\n"
                f"🍿 ¡Felicitaciones por tu dedicación cinematográfica!"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            # Agregar puntos bonus
            from db import add_points
            add_points(
                user_id=0,  # Se extraerá del contexto
                username=username,
                points=achievement['points_bonus'],
                hashtag='(logro)',
                message_text=f"Logro: {achievement['name']}",
                chat_id=chat_id,
                message_id=0,
                is_challenge_bonus=True,
                context=context
            )
    
    except Exception as e:
        print(f"[ERROR] notify_achievements: {e}")

# ========== COMANDOS DE USUARIO ==========

async def cmd_mis_logros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para ver logros del usuario"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        user_achievements = get_user_achievements(user_id)
        
        if not user_achievements:
            await update.message.reply_text(
                "🏆 **TUS LOGROS**\n\n"
                "🎬 Aún no has desbloqueado ningún logro\n\n"
                "💡 **Usa hashtags y participa activamente para desbloquear logros épicos!**\n"
                "🏷️ `#aporte` `#reseña` `#crítica` `#recomendación`",
                parse_mode='Markdown'
            )
            return
        
        # Ordenar por fecha de desbloqueo
        user_achievements.sort(key=lambda x: x[1], reverse=True)
        
        achievements_text = f"🏆 **LOGROS DE {username.upper()}**\n\n"
        
        rarity_emojis = {
            "common": "⚪",
            "uncommon": "🟢", 
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟡"
        }
        
        total_bonus_points = 0
        
        for achievement_id, unlock_date in user_achievements:
            achievement = ACHIEVEMENTS.get(achievement_id)
            if achievement:
                rarity_emoji = rarity_emojis.get(achievement['rarity'], "⚪")
                
                try:
                    date_formatted = datetime.fromisoformat(unlock_date).strftime("%d/%m/%Y")
                except:
                    date_formatted = unlock_date[:10]
                
                achievements_text += (
                    f"{rarity_emoji} **{achievement['name']}**\n"
                    f"   📝 {achievement['description']}\n"
                    f"   📅 Desbloqueado: {date_formatted}\n"
                    f"   🏆 Bonus: +{achievement['points_bonus']} pts\n\n"
                )
                
                total_bonus_points += achievement['points_bonus']
        
        achievements_text += (
            f"📊 **Resumen:**\n"
            f"🏆 Logros desbloqueados: {len(user_achievements)}/{len(ACHIEVEMENTS)}\n"
            f"💎 Puntos bonus totales: {total_bonus_points}\n"
            f"📈 Progreso: {len(user_achievements)/len(ACHIEVEMENTS)*100:.1f}%"
        )
        
        await update.message.reply_text(achievements_text, parse_mode='Markdown')
        
    except Exception as e:
        print(f"[ERROR] cmd_mis_logros: {e}")
        await update.message.reply_text("❌ Error al obtener logros")

async def cmd_todos_los_logros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para ver todos los logros disponibles"""
    try:
        user_id = update.effective_user.id
        user_achievements_ids = [aid for aid, _ in get_user_achievements(user_id)]
        
        achievements_text = "🏆 **TODOS LOS LOGROS DISPONIBLES**\n\n"
        
        rarity_emojis = {
            "common": "⚪",
            "uncommon": "🟢",
            "rare": "🔵", 
            "epic": "🟣",
            "legendary": "🟡"
        }
        
        # Agrupar por rareza
        by_rarity = {}
        for achievement in ACHIEVEMENTS.values():
            rarity = achievement['rarity']
            if rarity not in by_rarity:
                by_rarity[rarity] = []
            by_rarity[rarity].append(achievement)
        
        rarity_order = ["common", "uncommon", "rare", "epic", "legendary"]
        
        for rarity in rarity_order:
            if rarity not in by_rarity:
                continue
                
            achievements_text += f"**{rarity_emojis[rarity]} {rarity.upper()}**\n"
            
            for achievement in by_rarity[rarity]:
                status = "✅" if achievement['id'] in user_achievements_ids else "🔒"
                achievements_text += (
                    f"{status} **{achievement['name']}** (+{achievement['points_bonus']})\n"
                    f"    {achievement['description']}\n\n"
                )
        
        progress = len(user_achievements_ids) / len(ACHIEVEMENTS) * 100
        achievements_text += f"📊 **Tu progreso: {progress:.1f}% ({len(user_achievements_ids)}/{len(ACHIEVEMENTS)})**"
        
        await update.message.reply_text(achievements_text, parse_mode='Markdown')
        
    except Exception as e:
        print(f"[ERROR] cmd_todos_los_logros: {e}")
        await update.message.reply_text("❌ Error al mostrar logros")

# ========== INTEGRACIÓN ==========

def setup_achievements():
    """Configurar sistema de logros"""
    create_achievements_tables()
    print("[INFO] 🏆 Sistema de logros inicializado")
