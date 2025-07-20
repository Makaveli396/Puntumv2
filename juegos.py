#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import asyncio
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import add_points, get_connection

# Sistema de almacenamiento de juegos activos (en memoria)
active_games: Dict[int, Dict] = {}

# Base de datos de películas para los juegos
MOVIES_DB = [
    {
        "title": "El Padrino", "year": 1972, "genre": "Drama",
        "director": "Francis Ford Coppola", "difficulty": 2,
        "hints": ["Mafia italiana", "Marlon Brando", "Oscar a mejor película"],
        "emojis": "👨‍👨‍👦 🔫 🍷 💰"
    },
    {
        "title": "Pulp Fiction", "year": 1994, "genre": "Crime",
        "director": "Quentin Tarantino", "difficulty": 3,
        "hints": ["Narrativa no lineal", "John Travolta", "Vincent Vega"],
        "emojis": "🍔 💉 🕺 🎯"
    },
    {
        "title": "Forrest Gump", "year": 1994, "genre": "Drama",
        "director": "Robert Zemeckis", "difficulty": 2,
        "hints": ["Tom Hanks", "Chocolates", "Ping pong"],
        "emojis": "🏃‍♂️ 🍫 🏓 🪶"
    },
    {
        "title": "Matrix", "year": 1999, "genre": "Sci-Fi",
        "director": "Las Wachowski", "difficulty": 2,
        "hints": ["Realidad virtual", "Keanu Reeves", "Píldora roja"],
        "emojis": "💊 🕶️ 💻 🔌"
    },
    {
        "title": "Titanic", "year": 1997, "genre": "Romance",
        "director": "James Cameron", "difficulty": 1,
        "hints": ["Barco hundido", "Leonardo DiCaprio", "Iceberg"],
        "emojis": "🚢 ❄️ 💎 💔"
    },
    {
        "title": "El Señor de los Anillos", "year": 2001, "genre": "Fantasy",
        "director": "Peter Jackson", "difficulty": 3,
        "hints": ["Hobbit", "Anillo de poder", "Tierra Media"],
        "emojis": "💍 🧙‍♂️ 🗡️ 🏔️"
    },
    {
        "title": "Jurassic Park", "year": 1993, "genre": "Adventure",
        "director": "Steven Spielberg", "difficulty": 2,
        "hints": ["Dinosaurios", "Isla", "ADN"],
        "emojis": "🦕 🧬 🏝️ 🚁"
    },
    {
        "title": "Star Wars", "year": 1977, "genre": "Sci-Fi",
        "director": "George Lucas", "difficulty": 1,
        "hints": ["Galaxia lejana", "Luke Skywalker", "Fuerza"],
        "emojis": "⭐ 🗡️ 🤖 🚀"
    },
    {
        "title": "Casablanca", "year": 1942, "genre": "Romance",
        "director": "Michael Curtiz", "difficulty": 4,
        "hints": ["Humphrey Bogart", "Marruecos", "Segunda Guerra"],
        "emojis": "✈️ 🎹 💔 🌍"
    },
    {
        "title": "El Rey León", "year": 1994, "genre": "Animation",
        "director": "Roger Allers", "difficulty": 1,
        "hints": ["Simba", "Hakuna Matata", "África"],
        "emojis": "🦁 👑 🌅 🎵"
    }
]

# Preguntas de trivia
TRIVIA_QUESTIONS = [
    {
        "question": "¿Quién dirigió la película 'Inception'?",
        "options": ["Christopher Nolan", "David Fincher", "Denis Villeneuve", "Ridley Scott"],
        "correct": 0,
        "points": 10
    },
    {
        "question": "¿En qué año se estrenó 'Pulp Fiction'?",
        "options": ["1992", "1994", "1996", "1998"],
        "correct": 1,
        "points": 8
    },
    {
        "question": "¿Cuál de estos actores no aparece en 'El Padrino'?",
        "options": ["Al Pacino", "Robert De Niro", "Marlon Brando", "Jack Nicholson"],
        "correct": 3,
        "points": 12
    },
    {
        "question": "¿Qué película ganó el Oscar a Mejor Película en 2020?",
        "options": ["1917", "Joker", "Parásitos", "Érase una vez en Hollywood"],
        "correct": 2,
        "points": 15
    },
    {
        "question": "¿Quién compuso la música de 'Star Wars'?",
        "options": ["Hans Zimmer", "John Williams", "Danny Elfman", "Alan Silvestri"],
        "correct": 1,
        "points": 10
    }
]

def initialize_games_system():
    """Inicializar el sistema de juegos"""
    create_games_tables()
    print("[INFO] ✅ Sistema de juegos inicializado")

def create_games_tables():
    """Crear tablas para estadísticas de juegos"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_stats (
            user_id INTEGER,
            username TEXT,
            game_type TEXT,
            games_played INTEGER DEFAULT 0,
            games_won INTEGER DEFAULT 0,
            total_points INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            last_played TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, game_type)
        )
    """)
    
    conn.commit()
    conn.close()

async def cleanup_games_periodically():
    """Limpiar juegos inactivos cada 30 minutos"""
    while True:
        try:
            await asyncio.sleep(1800)  # 30 minutos
            current_time = datetime.now()
            
            to_remove = []
            for chat_id, game in active_games.items():
                if current_time - game.get('started_at', current_time) > timedelta(minutes=30):
                    to_remove.append(chat_id)
            
            for chat_id in to_remove:
                del active_games[chat_id]
                
            if to_remove:
                print(f"[INFO] Limpieza de juegos: {len(to_remove)} juegos inactivos eliminados")
                
        except Exception as e:
            print(f"[ERROR] Error en limpieza de juegos: {e}")

# COMANDOS DE JUEGOS

async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iniciar trivia de películas"""
    chat_id = update.effective_chat.id
    
    if chat_id in active_games:
        await update.message.reply_text(
            "🎮 Ya hay un juego activo en este chat.\n"
            "Usa /rendirse para abandonarlo y empezar uno nuevo."
        )
        return
    
    # Seleccionar pregunta aleatoria
    question_data = random.choice(TRIVIA_QUESTIONS)
    
    # Crear juego
    active_games[chat_id] = {
        'type': 'trivia',
        'question': question_data,
        'started_at': datetime.now(),
        'participants': []
    }
    
    # Crear teclado con opciones
    keyboard = []
    for i, option in enumerate(question_data['options']):
        keyboard.append([InlineKeyboardButton(
            f"{chr(65+i)}. {option}", 
            callback_data=f"trivia_{i}_{chat_id}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    trivia_text = f"""
🎬 **CINEMATRIVIA** 🍿

**Pregunta:** {question_data['question']}

💎 **Puntos en juego:** {question_data['points']}

👆 **Selecciona tu respuesta:**
    """
    
    await update.message.reply_text(
        trivia_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def cmd_adivinapelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar película por pistas"""
    chat_id = update.effective_chat.id
    
    if chat_id in active_games:
        await update.message.reply_text(
            "🎮 Ya hay un juego activo en este chat.\n"
            "Usa /rendirse para abandonarlo y empezar uno nuevo."
        )
        return
    
    # Seleccionar película aleatoria
    movie = random.choice(MOVIES_DB)
    
    # Crear juego
    active_games[chat_id] = {
        'type': 'guess_movie',
        'movie': movie,
        'hints_used': 0,
        'started_at': datetime.now(),
        'participants': []
    }
    
    points = 20 - (movie['difficulty'] * 3)
    
    game_text = f"""
🎬 **ADIVINA LA PELÍCULA** 🕵️‍♂️

**Primera pista:** {movie['hints'][0]}

🎯 **Dificultad:** {'⭐' * movie['difficulty']} ({movie['difficulty']}/5)
💎 **Puntos:** {points}

💡 **Para jugar:**
• Escribe el nombre de la película
• Usa /pista para más ayuda (-5 puntos)
• Usa /rendirse para abandonar

¡A adivinar! 🍿
    """
    
    await update.message.reply_text(game_text, parse_mode='Markdown')

async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar película por emojis"""
    chat_id = update.effective_chat.id
    
    if chat_id in active_games:
        await update.message.reply_text(
            "🎮 Ya hay un juego activo en este chat.\n"
            "Usa /rendirse para abandonarlo y empezar uno nuevo."
        )
        return
    
    # Seleccionar película con emojis
    movies_with_emojis = [m for m in MOVIES_DB if m.get('emojis')]
    if not movies_with_emojis:
        await update.message.reply_text("😅 Juego temporalmente no disponible.")
        return
    
    movie = random.choice(movies_with_emojis)
    
    # Crear juego
    active_games[chat_id] = {
        'type': 'emoji_movie',
        'movie': movie,
        'started_at': datetime.now(),
        'participants': []
    }
    
    points = 15 + (movie['difficulty'] * 2)
    
    game_text = f"""
🎬 **PELÍCULA EN EMOJIS** 😎

{movie['emojis']}

🎯 **Dificultad:** {'⭐' * movie['difficulty']} ({movie['difficulty']}/5)
💎 **Puntos:** {points}

💡 **Para jugar:**
• Escribe el nombre de la película
• Usa /pista para ayuda (-3 puntos)
• Usa /rendirse para abandonar

¿Puedes adivinar qué película es? 🤔
    """
    
    await update.message.reply_text(game_text, parse_mode='Markdown')

async def cmd_pista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pedir pista en juego activo"""
    chat_id = update.effective_chat.id
    
    if chat_id not in active_games:
        await update.message.reply_text(
            "🚫 No hay juegos activos en este chat.\n"
            "Inicia uno con /cinematrivia, /adivinapelicula o /emojipelicula"
        )
        return
    
    game = active_games[chat_id]
    
    if game['type'] == 'trivia':
        await update.message.reply_text(
            "💡 En trivia no hay pistas adicionales.\n"
            "¡Confía en tu conocimiento cinematográfico! 🎬"
        )
        return
    
    if game['type'] == 'guess_movie':
        hints_used = game['hints_used']
        movie = game['movie']
        
        if hints_used >= len(movie['hints']) - 1:
            await update.message.reply_text(
                "🚫 Ya has usado todas las pistas disponibles.\n"
                "¡Es hora de adivinar! 🎯"
            )
            return
        
        # Mostrar siguiente pista
        hints_used += 1
        game['hints_used'] = hints_used
        
        next_hint = movie['hints'][hints_used]
        penalty = 5 if game['type'] == 'guess_movie' else 3
        
        hint_text = f"""
💡 **PISTA {hints_used + 1}:** {next_hint}

⚠️ **Penalización:** -{penalty} puntos
🎯 **Puntos restantes:** {max(5, 20 - (movie['difficulty'] * 3) - (hints_used * penalty))}
        """
        
        await update.message.reply_text(hint_text, parse_mode='Markdown')
    
    elif game['type'] == 'emoji_movie':
        # Para emoji, dar pista del año y género
        movie = game['movie']
        hint_text = f"""
💡 **PISTA EXTRA:**
📅 Año: {movie['year']}
🎭 Género: {movie['genre']}

⚠️ **Penalización:** -3 puntos
        """
        await update.message.reply_text(hint_text, parse_mode='Markdown')

async def cmd_rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rendirse en juego activo"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id not in active_games:
        await update.message.reply_text("🚫 No hay juegos activos para abandonar.")
        return
    
    game = active_games[chat_id]
    
    if game['type'] == 'trivia':
        question = game['question']
        correct_answer = question['options'][question['correct']]
        surrender_text = f"""
🏳️ **Juego abandonado**

❓ **Pregunta:** {question['question']}
✅ **Respuesta correcta:** {correct_answer}

¡No te rindas! Inténtalo de nuevo con /cinematrivia 🎬
        """
    else:
        movie = game['movie']
        surrender_text = f"""
🏳️ **Juego abandonado**

🎬 **La película era:** {movie['title']} ({movie['year']})
🎭 **Director:** {movie['director']}
🎯 **Género:** {movie['genre']}

¡Mejor suerte la próxima vez! 🍿
        """
    
    # Actualizar estadísticas (juego jugado pero no ganado)
    update_game_stats(user.id, user.username or user.first_name, game['type'], won=False)
    
    # Eliminar juego
    del active_games[chat_id]
    
    await update.message.reply_text(surrender_text, parse_mode='Markdown')

async def cmd_estadisticasjuegos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver estadísticas de juegos del usuario"""
    user = update.effective_user
    stats = get_user_game_stats(user.id)
    
    if not stats:
        await update.message.reply_text(
            "📊 Aún no tienes estadísticas de juegos.\n"
            "¡Juega con /cinematrivia, /adivinapelicula o /emojipelicula!"
        )
        return
    
    stats_text = f"🎮 **ESTADÍSTICAS DE JUEGOS**\n👤 **{user.first_name}**\n\n"
    
    total_played = sum(s['games_played'] for s in stats.values())
    total_won = sum(s['games_won'] for s in stats.values())
    win_rate = (total_won / total_played * 100) if total_played > 0 else 0
    
    stats_text += f"📈 **Resumen General:**\n"
    stats_text += f"🎯 Partidas jugadas: {total_played}\n"
    stats_text += f"🏆 Partidas ganadas: {total_won}\n"
    stats_text += f"📊 Tasa de éxito: {win_rate:.1f}%\n\n"
    
    game_names = {
        'trivia': '🎬 Cinematrivia',
        'guess_movie': '🕵️‍♂️ Adivina Película',
        'emoji_movie': '😎 Película Emojis'
    }
    
    for game_type, data in stats.items():
        if data['games_played'] > 0:
            name = game_names.get(game_type, game_type.title())
            rate = (data['games_won'] / data['games_played'] * 100)
            
            stats_text += f"{name}:\n"
            stats_text += f"  🎮 Jugadas: {data['games_played']}\n"
            stats_text += f"  🏆 Ganadas: {data['games_won']} ({rate:.1f}%)\n"
            stats_text += f"  💎 Puntos: {data['total_points']}\n"
            stats_text += f"  🔥 Mejor racha: {data['best_streak']}\n\n"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def cmd_top_jugadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ranking de mejores jugadores"""
    top_players = get_top_game_players()
    
    if not top_players:
        await update.message.reply_text("🎮 Aún no hay jugadores en el ranking.")
        return
    
    ranking_text = "🏆 **TOP JUGADORES DE JUEGOS** 🎮\n\n"
    
    medals = ["🥇", "🥈", "🥉"] + ["🎯"] * 7
    
    for i, (username, total_points, games_won, games_played) in enumerate(top_players[:10]):
        medal = medals[i] if i < len(medals) else "🎯"
        win_rate = (games_won / games_played * 100) if games_played > 0 else 0
        
        ranking_text += f"{medal} **{i+1}.** {username}\n"
        ranking_text += f"    💎 {total_points} pts | 🏆 {games_won}/{games_played} ({win_rate:.1f}%)\n\n"
    
    await update.message.reply_text(ranking_text, parse_mode='Markdown')

# MANEJADORES DE EVENTOS

async def handle_trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar respuestas de trivia"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Parsear callback data: "trivia_[respuesta]_[chat_id]"
        parts = query.data.split('_')
        if len(parts) != 3 or parts[0] != 'trivia':
            return
            
        selected_answer = int(parts[1])
        chat_id = int(parts[2])
        
        if chat_id not in active_games or active_games[chat_id]['type'] != 'trivia':
            await query.edit_message_text("❌ Este juego ya no está activo.")
            return
        
        game = active_games[chat_id]
        question = game['question']
        user = query.from_user
        
        # Verificar si ya participó
        if user.id in game['participants']:
            await query.answer("⚠️ Ya participaste en esta pregunta.", show_alert=True)
            return
        
        game['participants'].append(user.id)
        
        is_correct = selected_answer == question['correct']
        correct_answer = question['options'][question['correct']]
        
        if is_correct:
            # Ganar puntos
            points = question['points']
            add_points(
                user_id=user.id,
                username=user.username or user.first_name,
                points=points,
                hashtag='(cinematrivia)',
                chat_id=chat_id,
                is_challenge_bonus=True,
                context=context
            )
            
            # Actualizar estadísticas
            update_game_stats(user.id, user.username or user.first_name, 'trivia', won=True, points=points)
            
            result_text = f"""
✅ **¡CORRECTO!** 🎉

👤 {user.mention_html()}
💎 **+{points} puntos**
✨ Respuesta: {correct_answer}

¡Excelente conocimiento cinematográfico! 🎬
            """
        else:
            # Actualizar estadísticas (participó pero no ganó)
            update_game_stats(user.id, user.username or user.first_name, 'trivia', won=False)
            
            result_text = f"""
❌ **Incorrecto** 😅

👤 {user.mention_html()}
✅ **Respuesta correcta:** {correct_answer}

¡Sigue intentando! 💪
            """
        
        # Eliminar juego después de primera respuesta
        del active_games[chat_id]
        
        await query.edit_message_text(result_text, parse_mode='HTML')
        
    except Exception as e:
        print(f"[ERROR] handle_trivia_callback: {e}")
        await query.edit_message_text("❌ Error procesando respuesta.")

async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes durante juegos activos"""
    if not update.message or not update.message.text:
        return
    
    chat_id = update.effective_chat.id
    
    if chat_id not in active_games:
        return  # No hay juego activo
    
    game = active_games[chat_id]
    user = update.effective_user
    message_text = update.message.text.lower().strip()
    
    # Solo procesar juegos de adivinanza
    if game['type'] not in ['guess_movie', 'emoji_movie']:
        return
    
    movie = game['movie']
    correct_titles = [
        movie['title'].lower(),
        movie['title'].lower().replace('el ', '').replace('la ', '').replace('los ', '').replace('las ', '')
    ]
    
    # Verificar si la respuesta es correcta
    is_correct = any(title in message_text or message_text in title for title in correct_titles)
    
    if is_correct:
        # Calcular puntos
        base_points = 20 if game['type'] == 'guess_movie' else 15
        difficulty_bonus = movie['difficulty'] * (3 if game['type'] == 'guess_movie' else 2)
        hints_penalty = game.get('hints_used', 0) * (5 if game['type'] == 'guess_movie' else 3)
        
        total_points = max(5, base_points - (movie['difficulty'] * 2) + difficulty_bonus - hints_penalty)
        
        # Agregar puntos
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=total_points,
            hashtag=f'({game["type"]})',
            chat_id=chat_id,
            is_challenge_bonus=True,
            context=context
        )
        
        # Actualizar estadísticas
        update_game_stats(user.id, user.username or user.first_name, game['type'], won=True, points=total_points)
        
        # Respuesta de victoria
        victory_text = f"""
🎉 **¡CORRECTO!** 🏆

👤 {user.mention_html()}
🎬 **{movie['title']}** ({movie['year']})
🎭 Director: {movie['director']}
💎 **+{total_points} puntos**

¡Excelente! 🍿 ¡Juega de nuevo cuando quieras!
        """
        
        # Eliminar juego
        del active_games[chat_id]
        
        await update.message.reply_text(victory_text, parse_mode='HTML')

# FUNCIONES DE BASE DE DATOS

def update_game_stats(user_id: int, username: str, game_type: str, won: bool = False, points: int = 0):
    """Actualizar estadísticas de juegos del usuario"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener estadísticas actuales
        cursor.execute(
            "SELECT games_played, games_won, total_points, best_streak, current_streak FROM game_stats WHERE user_id = ? AND game_type = ?",
            (user_id, game_type)
        )
        current = cursor.fetchone()
        
        if current:
            games_played, games_won, total_points, best_streak, current_streak = current
            games_played += 1
            total_points += points
            
            if won:
                games_won += 1
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0
            
            cursor.execute(
                """UPDATE game_stats 
                   SET games_played = ?, games_won = ?, total_points = ?, 
                       best_streak = ?, current_streak = ?, last_played = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND game_type = ?""",
                (games_played, games_won, total_points, best_streak, current_streak, user_id, game_type)
            )
        else:
            # Crear nueva entrada
            cursor.execute(
                """INSERT INTO game_stats 
                   (user_id, username, game_type, games_played, games_won, total_points, best_streak, current_streak)
                   VALUES (?, ?, ?, 1, ?, ?, ?, ?)""",
                (user_id, username, game_type, 1 if won else 0, points, 1 if won else 0, 1 if won else 0)
            )
        
        conn.commit()
        
    except Exception as e:
        print(f"[ERROR] update_game_stats: {e}")
    finally:
        conn.close()

def get_user_game_stats(user_id: int) -> Dict:
    """Obtener estadísticas de juegos del usuario"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT game_type, games_played, games_won, total_points, best_streak, current_streak FROM game_stats WHERE user_id = ?",
            (user_id,)
        )
        results = cursor.fetchall()
        
        stats = {}
        for game_type, played, won, points, best_streak, current_streak in results:
            stats[game_type] = {
                'games_played': played,
                'games_won': won,
                'total_points': points,
                'best_streak': best_streak,
                'current_streak': current_streak
            }
        
        return stats
        
    except Exception as e:
        print(f"[ERROR] get_user_game_stats: {e}")
        return {}
    finally:
        conn.close()

def get_top_game_players(limit: int = 10) -> List[Tuple]:
    """Obtener ranking de mejores jugadores"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT username, SUM(total_points) as total_pts, SUM(games_won) as total_won, SUM(games_played) as total_played
               FROM game_stats 
               GROUP BY user_id, username
               HAVING total_played > 0
               ORDER BY total_pts DESC, total_won DESC
               LIMIT ?""",
            (limit,)
        )
        
        return cursor.fetchall()
        
    except Exception as e:
        print(f"[ERROR] get_top_game_players: {e}")
        return []
    finally:
        conn.close()
