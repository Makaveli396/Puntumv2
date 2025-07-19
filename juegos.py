#!/usr/bin/env python3
import random
import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Optional, Tuple, List, Dict, Any

# ========== CONSTANTES DE CONFIGURACIÓN ==========
GAME_TIMEOUT_HOURS = 1
TRIVIA_TIME_LIMIT = 60  # segundos
TRIVIA_POINTS = 25
GUESS_MOVIE_BASE_POINTS = 30
GUESS_MOVIE_HINT_PENALTY = 5
EMOJI_MOVIE_POINTS = 20

# ========== MANEJO DE ERRORES Y LOGGING ==========
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_db_operation(operation_name: str):
    """Decorador para operaciones seguras de BD"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            except sqlite3.Error as e:
                logger.error(f"[ERROR] {operation_name}: {e}")
                return None
            except Exception as e:
                logger.error(f"[ERROR] Error inesperado en {operation_name}: {e}")
                return None
        return wrapper
    return decorator

# ========== BASE DE DATOS DE JUEGOS ==========

@safe_db_operation("crear tablas de juegos")
def create_games_tables():
    """Crear tablas para mini-juegos con mejor estructura"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # Tabla para estadísticas de juegos - mejorada con índices
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_stats (
            user_id INTEGER,
            username TEXT,
            game_type TEXT,
            correct_answers INTEGER DEFAULT 0,
            total_attempts INTEGER DEFAULT 0,
            points_earned INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            last_played TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, game_type)
        )
    ''')
    
    # Añadir índices para mejor rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_stats_user ON game_stats(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_stats_type ON game_stats(game_type)')
    
    # Tabla para sesiones activas - mejorada con más información
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            game_type TEXT,
            current_question TEXT,
            correct_answer TEXT,
            options TEXT,
            start_time TEXT,
            attempts INTEGER DEFAULT 0,
            hints_used INTEGER DEFAULT 0,
            max_hints INTEGER DEFAULT 0,
            points_available INTEGER DEFAULT 0,
            expires_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, user_id, game_type)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_active_games_user ON active_games(chat_id, user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_active_games_expires ON active_games(expires_at)')
    
    # Tabla para historial de partidas (opcional, para analytics)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            game_type TEXT,
            question TEXT,
            user_answer TEXT,
            correct_answer TEXT,
            is_correct BOOLEAN,
            points_earned INTEGER,
            hints_used INTEGER,
            time_taken INTEGER, -- en segundos
            played_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("🎮 Tablas de mini-juegos creadas con optimizaciones")

# ========== DATOS DE JUEGOS (Mantenidos, pero con mejoras) ==========

class GameData:
    """Clase para manejar datos de juegos de forma más organizada"""
    
    TRIVIA_QUESTIONS = [
        {
            "question": "¿Quién dirigió 'Pulp Fiction' (1994)?",
            "options": ["A) Martin Scorsese", "B) Quentin Tarantino", "C) Francis Ford Coppola", "D) Stanley Kubrick"],
            "correct": "B",
            "explanation": "Quentin Tarantino dirigió esta obra maestra del cine independiente",
            "difficulty": "medium"
        },
        {
            "question": "¿En qué año se estrenó 'El Padrino'?",
            "options": ["A) 1970", "B) 1971", "C) 1972", "D) 1973"],
            "correct": "C",
            "explanation": "El Padrino se estrenó en 1972 y ganó 3 premios Oscar",
            "difficulty": "easy"
        },
        {
            "question": "¿Cuál es la película más taquillera de todos los tiempos?",
            "options": ["A) Titanic", "B) Avatar (2009)", "C) Avengers: Endgame", "D) Star Wars: El despertar de la fuerza"],
            "correct": "B",
            "explanation": "Avatar (2009) recaudó más de $2.8 mil millones mundialmente",
            "difficulty": "medium"
        },
        {
            "question": "¿Qué actor interpretó a Neo en 'The Matrix'?",
            "options": ["A) Will Smith", "B) Johnny Depp", "C) Keanu Reeves", "D) Leonardo DiCaprio"],
            "correct": "C",
            "explanation": "Keanu Reeves inmortalizó al personaje de Neo",
            "difficulty": "easy"
        },
        {
            "question": "¿Cuántos Oscars ganó 'El Señor de los Anillos: El Retorno del Rey'?",
            "options": ["A) 9", "B) 10", "C) 11", "D) 12"],
            "correct": "C",
            "explanation": "Ganó 11 Oscars, récord compartido con Ben-Hur y Titanic",
            "difficulty": "hard"
        },
        {
            "question": "¿En qué película aparece la frase 'Que la fuerza te acompañe'?",
            "options": ["A) Star Trek", "B) Star Wars", "C) Guardianes de la Galaxia", "D) Blade Runner"],
            "correct": "B",
            "explanation": "Esta icónica frase es de la saga Star Wars",
            "difficulty": "easy"
        },
        {
            "question": "¿Quién compuso la música de 'Tiburón' (1975)?",
            "options": ["A) Hans Zimmer", "B) John Williams", "C) Danny Elfman", "D) Ennio Morricone"],
            "correct": "B",
            "explanation": "John Williams creó esa terrorífica y simple melodía",
            "difficulty": "medium"
        },
        {
            "question": "¿Qué director es conocido por sus películas de suspenso como 'Psicosis' y 'Vértigo'?",
            "options": ["A) Brian De Palma", "B) David Lynch", "C) Alfred Hitchcock", "D) Roman Polanski"],
            "correct": "C",
            "explanation": "Alfred Hitchcock, el maestro del suspenso",
            "difficulty": "medium"
        },
        {
            "question": "¿Qué película de 2010 ganó el Oscar a Mejor Película?",
            "options": ["A) Inception", "B) The Social Network", "C) The King's Speech", "D) Black Swan"],
            "correct": "C",
            "explanation": "The King's Speech ganó el Oscar a Mejor Película en 2011",
            "difficulty": "hard"
        },
        {
            "question": "¿Quién interpretó al Joker en 'The Dark Knight' (2008)?",
            "options": ["A) Jack Nicholson", "B) Heath Ledger", "C) Joaquin Phoenix", "D) Jared Leto"],
            "correct": "B",
            "explanation": "Heath Ledger dio una actuación legendaria como el Joker",
            "difficulty": "medium"
        }
    ]
    
    MOVIE_PUZZLES = [
        {
            "hints": [
                "🔍 Drama carcelario de 1994",
                "🔍 Protagonistas: Tim Robbins y Morgan Freeman",
                "🔍 Prisión de Shawshank",
                "🔍 'Get busy living or get busy dying'"
            ],
            "answer": ["shawshank", "sueños de fuga", "cadena perpetua"],
            "title": "Sueños de Fuga (The Shawshank Redemption)",
            "difficulty": "medium"
        },
        {
            "hints": [
                "🔍 Ciencia ficción, 1999",
                "🔍 Realidad virtual y píldoras",
                "🔍 Neo, Morfeo, Trinity",
                "🔍 '¿Píldora roja o azul?'"
            ],
            "answer": ["matrix", "the matrix"],
            "title": "The Matrix",
            "difficulty": "easy"
        },
        {
            "hints": [
                "🔍 Épica espacial, 1977",
                "🔍 Luke Skywalker y la Princesa Leia",
                "🔍 Darth Vader y la Estrella de la Muerte",
                "🔍 'Que la fuerza te acompañe'"
            ],
            "answer": ["star wars", "una nueva esperanza", "la guerra de las galaxias"],
            "title": "Star Wars: Una Nueva Esperanza",
            "difficulty": "easy"
        },
        {
            "hints": [
                "🔍 Thriller psicológico, 1999",
                "🔍 Brad Pitt y Edward Norton",
                "🔍 Reglas que no se pueden mencionar",
                "🔍 'Su nombre era Robert Paulson'"
            ],
            "answer": ["fight club", "el club de la pelea", "club de la pelea"],
            "title": "Fight Club",
            "difficulty": "hard"
        },
        {
            "hints": [
                "🔍 Romance épico, 1997",
                "🔍 Leonardo DiCaprio y Kate Winslet",
                "🔍 Barco que se hunde",
                "🔍 'I'm the king of the world!'"
            ],
            "answer": ["titanic"],
            "title": "Titanic",
            "difficulty": "easy"
        },
        {
            "hints": [
                "🔍 Animación de Pixar, 1995",
                "🔍 Woody y Buzz Lightyear",
                "🔍 Juguetes que cobran vida",
                "🔍 'To infinity and beyond!'"
            ],
            "answer": ["toy story", "toy story 1"],
            "title": "Toy Story",
            "difficulty": "easy"
        }
    ]
    
    EMOJI_MOVIES = [
        {
            "emojis": "🦁👑🌍",
            "answer": ["el rey leon", "rey leon", "the lion king", "lion king"],
            "title": "El Rey León",
            "difficulty": "easy"
        },
        {
            "emojis": "🚢💕🧊",
            "answer": ["titanic"],
            "title": "Titanic",
            "difficulty": "easy"
        },
        {
            "emojis": "🕷️👨🏻‍🎓🏢",
            "answer": ["spiderman", "spider-man", "hombre araña"],
            "title": "Spider-Man",
            "difficulty": "easy"
        },
        {
            "emojis": "🤖🚗🌍",
            "answer": ["transformers"],
            "title": "Transformers",
            "difficulty": "medium"
        },
        {
            "emojis": "🍫🏭👶",
            "answer": ["charlie y la fabrica de chocolate", "charlie fabrica chocolate", "willy wonka"],
            "title": "Charlie y la Fábrica de Chocolate",
            "difficulty": "medium"
        },
        {
            "emojis": "🦇🌃🃏",
            "answer": ["batman", "el caballero de la noche", "dark knight"],
            "title": "Batman / El Caballero de la Noche",
            "difficulty": "medium"
        },
        {
            "emojis": "🧙‍♂️⚡💫",
            "answer": ["harry potter"],
            "title": "Harry Potter",
            "difficulty": "easy"
        },
        {
            "emojis": "🐠🐟🌊",
            "answer": ["finding nemo", "buscando a nemo", "nemo"],
            "title": "Buscando a Nemo",
            "difficulty": "easy"
        },
        {
            "emojis": "💍👑⚔️",
            "answer": ["lord of the rings", "señor de los anillos", "lotr"],
            "title": "El Señor de los Anillos",
            "difficulty": "medium"
        },
        {
            "emojis": "👻🚫☎️",
            "answer": ["ghostbusters", "cazafantasmas"],
            "title": "Cazafantasmas",
            "difficulty": "medium"
        }
    ]

# ========== FUNCIONES DE JUEGO OPTIMIZADAS ==========

class GameManager:
    """Clase para manejar la lógica de juegos de forma más organizada"""
    
    @staticmethod
    @safe_db_operation("guardar estadísticas de juego")
    def save_game_stats(user_id: int, username: str, game_type: str, correct: bool, points: int) -> bool:
        """Guardar estadísticas del juego con manejo mejorado de rachas"""
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        # Obtener estadísticas actuales
        cursor.execute('''
            SELECT current_streak, best_streak FROM game_stats 
            WHERE user_id = ? AND game_type = ?
        ''', (user_id, game_type))
        
        result = cursor.fetchone()
        current_streak = result[0] if result else 0
        best_streak = result[1] if result else 0
        
        # Calcular nueva racha
        if correct:
            new_streak = current_streak + 1
            new_best = max(best_streak, new_streak)
        else:
            new_streak = 0
            new_best = best_streak
        
        # Actualizar o insertar estadísticas
        cursor.execute('''
            INSERT OR REPLACE INTO game_stats (
                user_id, username, game_type, correct_answers, total_attempts, 
                points_earned, current_streak, best_streak, last_played, updated_at
            )
            VALUES (?, ?, ?, 
                COALESCE((SELECT correct_answers FROM game_stats WHERE user_id = ? AND game_type = ?), 0) + ?,
                COALESCE((SELECT total_attempts FROM game_stats WHERE user_id = ? AND game_type = ?), 0) + 1,
                COALESCE((SELECT points_earned FROM game_stats WHERE user_id = ? AND game_type = ?), 0) + ?,
                ?, ?, ?, ?
            )
        ''', (user_id, username, game_type, user_id, game_type, 1 if correct else 0, 
              user_id, game_type, user_id, game_type, points, new_streak, new_best,
              datetime.now().isoformat(), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    @safe_db_operation("iniciar juego activo")
    def start_active_game(chat_id: int, user_id: int, game_type: str, question: str, 
                         answer: str, options: str = "", max_hints: int = 0, points: int = 0) -> bool:
        """Iniciar una sesión de juego activa con mejores controles"""
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(hours=GAME_TIMEOUT_HOURS)
        
        cursor.execute('''
            INSERT OR REPLACE INTO active_games 
            (chat_id, user_id, game_type, current_question, correct_answer, options, 
             start_time, attempts, hints_used, max_hints, points_available, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?)
        ''', (chat_id, user_id, game_type, question, answer, options, 
              datetime.now().isoformat(), max_hints, points, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    @safe_db_operation("obtener juego activo")
    def get_active_game(chat_id: int, user_id: int, game_type: str) -> Optional[Tuple]:
        """Obtener juego activo con validación de expiración"""
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT current_question, correct_answer, options, attempts, hints_used, 
                   max_hints, points_available, expires_at
            FROM active_games 
            WHERE chat_id = ? AND user_id = ? AND game_type = ? AND expires_at > ?
        ''', (chat_id, user_id, game_type, datetime.now().isoformat()))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    @staticmethod
    @safe_db_operation("terminar juego activo")
    def end_active_game(chat_id: int, user_id: int, game_type: str) -> bool:
        """Terminar juego activo"""
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM active_games WHERE chat_id = ? AND user_id = ? AND game_type = ?', 
                       (chat_id, user_id, game_type))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    @safe_db_operation("actualizar intentos de juego")
    def update_game_attempts(chat_id: int, user_id: int, game_type: str, increment_hints: bool = False) -> bool:
        """Actualizar intentos y pistas usadas"""
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        if increment_hints:
            cursor.execute('''
                UPDATE active_games SET attempts = attempts + 1, hints_used = hints_used + 1
                WHERE chat_id = ? AND user_id = ? AND game_type = ?
            ''', (chat_id, user_id, game_type))
        else:
            cursor.execute('''
                UPDATE active_games SET attempts = attempts + 1
                WHERE chat_id = ? AND user_id = ? AND game_type = ?
            ''', (chat_id, user_id, game_type))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    @safe_db_operation("limpiar juegos expirados")
    def cleanup_expired_games() -> int:
        """Limpiar juegos expirados de forma más eficiente"""
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM active_games WHERE expires_at < ?', 
                       (datetime.now().isoformat(),))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"🧹 Limpiados {deleted} juegos expirados")
        
        return deleted
    
    @staticmethod
    def normalize_answer(answer: str) -> str:
        """Normalizar respuesta para comparación más flexible"""
        import unicodedata
        import re
        
        # Convertir a minúsculas
        answer = answer.lower()
        
        # Eliminar acentos
        answer = ''.join(c for c in unicodedata.normalize('NFD', answer)
                        if unicodedata.category(c) != 'Mn')
        
        # Eliminar caracteres especiales y espacios extra
        answer = re.sub(r'[^\w\s]', '', answer)
        answer = ' '.join(answer.split())
        
        return answer

# ========== COMANDOS DE MINI-JUEGOS MEJORADOS ==========

async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cinematrivia - Trivia cinematográfica mejorada"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "Usuario"
    chat_id = update.effective_chat.id
    
    # Verificar si ya hay un juego activo
    active_game = GameManager.get_active_game(chat_id, user_id, 'trivia')
    if active_game:
        await update.message.reply_text(
            "🎮 **¡Ya tienes una trivia activa!**\n\n"
            "Responde la pregunta actual o usa `/rendirse` para terminar el juego",
            parse_mode='Markdown'
        )
        return
    
    # Seleccionar pregunta aleatoria
    question_data = random.choice(GameData.TRIVIA_QUESTIONS)
    
    # Crear botones de respuesta con callback data único
    keyboard = []
    session_id = f"{chat_id}_{user_id}_{int(datetime.now().timestamp())}"
    for i, option in enumerate(question_data["options"]):
        option_letter = chr(65+i)  # A, B, C, D
        callback_data = f"trivia_{question_data['correct']}_{option_letter}_{session_id}"
        keyboard.append([InlineKeyboardButton(option, callback_data=callback_data)])
    
    # Añadir botón de rendirse
    keyboard.append([InlineKeyboardButton("🏳️ Rendirse", callback_data=f"surrender_trivia_{session_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Guardar juego activo
    GameManager.start_active_game(
        chat_id, user_id, 'trivia',
        question_data["question"],
        question_data["correct"],
        json.dumps(question_data),  # Guardar toda la data como JSON
        max_hints=0,
        points=TRIVIA_POINTS
    )
    
    # Enviar pregunta
    difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(question_data.get("difficulty", "medium"), "🟡")
    
    trivia_text = (
        f"🎬 **CINE-TRIVIA** 🍿\n\n"
        f"👤 **Jugador:** {username}\n"
        f"{difficulty_emoji} **Dificultad:** {question_data.get('difficulty', 'medium').title()}\n\n"
        f"❓ **{question_data['question']}**\n\n"
        f"⏰ **Tienes {TRIVIA_TIME_LIMIT} segundos para responder**\n"
        f"🏆 **+{TRIVIA_POINTS} puntos** si aciertas"
    )
    
    await update.message.reply_text(trivia_text, reply_markup=reply_markup, parse_mode='Markdown')

async def cmd_adivinapelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /adivinapelicula - Adivinar película con pistas mejorado"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "Usuario"
    chat_id = update.effective_chat.id
    
    # Verificar juego activo
    active_game = GameManager.get_active_game(chat_id, user_id, 'guess_movie')
    if active_game:
        await update.message.reply_text(
            "🎮 **¡Ya tienes un juego de adivinanza activo!**\n\n"
            "Escribe tu respuesta o usa `/rendirse` para terminar",
            parse_mode='Markdown'
        )
        return
    
    # Seleccionar película aleatoria
    movie_data = random.choice(GameData.MOVIE_PUZZLES)
    
    # Guardar juego activo
    GameManager.start_active_game(
        chat_id, user_id, 'guess_movie',
        movie_data["title"],
        json.dumps(movie_data["answer"]),  # Múltiples respuestas válidas
        json.dumps(movie_data),  # Toda la data
        max_hints=len(movie_data["hints"]) - 1,
        points=GUESS_MOVIE_BASE_POINTS
    )
    
    # Enviar primera pista
    difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(movie_data.get("difficulty", "medium"), "🟡")
    
    guess_text = (
        f"🔍 **ADIVINA LA PELÍCULA** 🎬\n\n"
        f"👤 **Jugador:** {username}\n"
        f"{difficulty_emoji} **Dificultad:** {movie_data.get('difficulty', 'medium').title()}\n\n"
        f"{movie_data['hints'][0]}\n\n"
        f"💡 **Escribe el título de la película**\n"
        f"🎯 **+{GUESS_MOVIE_BASE_POINTS} puntos** (máximo)\n"
        f"📝 **Comandos:** `/pista` para más ayuda, `/rendirse` para terminar"
    )
    
    await update.message.reply_text(guess_text, parse_mode='Markdown')

async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /emojipelicula - Adivinar película por emojis mejorado"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "Usuario"
    chat_id = update.effective_chat.id
    
    # Verificar juego activo
    active_game = GameManager.get_active_game(chat_id, user_id, 'emoji_movie')
    if active_game:
        await update.message.reply_text(
            "🎮 **¡Ya tienes un juego de emojis activo!**\n\n"
            "Adivina la película actual o usa `/rendirse`",
            parse_mode='Markdown'
        )
        return
    
    # Seleccionar película aleatoria
    emoji_data = random.choice(GameData.EMOJI_MOVIES)
    
    # Guardar juego activo
    GameManager.start_active_game(
        chat_id, user_id, 'emoji_movie',
        emoji_data["emojis"],
        json.dumps(emoji_data["answer"]),
        json.dumps(emoji_data),
        max_hints=1,  # Solo una pista: el título exacto
        points=EMOJI_MOVIE_POINTS
    )
    
    # Enviar emojis
    difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(emoji_data.get("difficulty", "easy"), "🟢")
    
    emoji_text = (
        f"🎭 **PELÍCULA EN EMOJIS** 🎬\n\n"
        f"👤 **Jugador:** {username}\n"
        f"{difficulty_emoji} **Dificultad:** {emoji_data.get('difficulty', 'easy').title()}\n\n"
        f"🎯 **Adivina esta película:**\n\n"
        f"# {emoji_data['emojis']}\n\n"
        f"💡 **Escribe el título**\n"
        f"🏆 **+{EMOJI_MOVIE_POINTS} puntos** por respuesta correcta\n"
        f"📝 **Usa** `/pista` **para obtener una pista o** `/rendirse` **para terminar**"
    )
    
    await update.message.reply_text(emoji_text, parse_mode='Markdown')

async def cmd_pista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /pista - Pedir pista adicional mejorado"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar juegos activos de adivinanza
    active_guess = GameManager.get_active_game(chat_id, user_id, 'guess_movie')
    active_emoji = GameManager.get_active_game(chat_id, user_id, 'emoji_movie')
    
    if not active_guess and not active_emoji:
        await update.message.reply_text("❌ No tienes un juego de adivinanza activo")
        return
    
    # Determinar tipo de juego
    if active_guess:
        game_type = 'guess_movie'
        active_game = active_guess
    else:
        game_type = 'emoji_movie'
        active_game = active_emoji

# Extraer datos del juego activo
    current_question, correct_answer, options, attempts, hints_used, max_hints, points_available, expires_at = active_game
    
    # Verificar si ya usó todas las pistas
    if hints_used >= max_hints:
        await update.message.reply_text("❌ Ya has usado todas las pistas disponibles")
        return
    
    # Cargar datos del juego
    try:
        game_data = json.loads(options)
    except:
        await update.message.reply_text("❌ Error al cargar datos del juego")
        return
    
    # Actualizar intentos y pistas
    GameManager.update_game_attempts(chat_id, user_id, game_type, increment_hints=True)
    
    if game_type == 'guess_movie':
        # Mostrar siguiente pista
        next_hint_index = hints_used + 1
        if next_hint_index < len(game_data["hints"]):
            hint = game_data["hints"][next_hint_index]
            remaining_hints = max_hints - (hints_used + 1)
            penalty = GUESS_MOVIE_HINT_PENALTY * (hints_used + 1)
            current_points = max(5, points_available - penalty)
            
            hint_text = (
                f"💡 **PISTA ADICIONAL** ({hints_used + 1}/{max_hints})\n\n"
                f"{hint}\n\n"
                f"🏆 **Puntos actuales:** {current_points}\n"
                f"💔 **Penalización por pista:** -{GUESS_MOVIE_HINT_PENALTY} puntos\n"
                f"📝 **Pistas restantes:** {remaining_hints}"
            )
        else:
            hint_text = f"❌ No hay más pistas disponibles"
    
    elif game_type == 'emoji_movie':
        # Para emoji, la pista es el título exacto
        hint_text = (
            f"💡 **PISTA ESPECIAL**\n\n"
            f"🎬 **Título exacto:** {game_data['title']}\n\n"
            f"¡Ahora debería ser más fácil! 😉"
        )
    
    await update.message.reply_text(hint_text, parse_mode='Markdown')

async def cmd_rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /rendirse - Rendirse en juego actual mejorado"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "Usuario"
    chat_id = update.effective_chat.id
    
    # Buscar juego activo
    active_games = []
    for game_type in ['trivia', 'guess_movie', 'emoji_movie']:
        game = GameManager.get_active_game(chat_id, user_id, game_type)
        if game:
            active_games.append((game_type, game))
    
    if not active_games:
        await update.message.reply_text("❌ No tienes ningún juego activo")
        return
    
    # Procesar rendición para cada juego activo
    for game_type, game_data in active_games:
        current_question, correct_answer, options, attempts, hints_used, max_hints, points_available, expires_at = game_data
        
        # Registrar estadísticas (intento fallido)
        GameManager.save_game_stats(user_id, username, game_type, False, 0)
        
        # Terminar juego
        GameManager.end_active_game(chat_id, user_id, game_type)
        
        # Mostrar respuesta correcta
        try:
            if game_type == 'trivia':
                game_info = json.loads(options)
                correct_option = next(opt for opt in game_info["options"] if opt.startswith(f"{correct_answer})"))
                answer_text = f"✅ **Respuesta correcta:** {correct_option}\n📚 {game_info.get('explanation', '')}"
            else:
                possible_answers = json.loads(correct_answer)
                answer_text = f"✅ **Respuesta correcta:** {possible_answers[0].title()}"
        except:
            answer_text = "✅ **Respuesta revelada**"
        
        surrender_text = (
            f"🏳️ **Te has rendido en {game_type.replace('_', ' ').title()}**\n\n"
            f"{answer_text}\n\n"
            f"💪 **¡No te rindas! Inténtalo de nuevo cuando quieras**"
        )
        
        await update.message.reply_text(surrender_text, parse_mode='Markdown')

async def cmd_estadisticas_juegos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /estadisticasjuegos - Ver estadísticas personales mejoradas"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "Usuario"
    
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # Obtener estadísticas por tipo de juego
    cursor.execute('''
        SELECT game_type, correct_answers, total_attempts, points_earned, 
               current_streak, best_streak, last_played
        FROM game_stats WHERE user_id = ?
        ORDER BY points_earned DESC
    ''', (user_id,))
    
    stats = cursor.fetchall()
    conn.close()
    
    if not stats:
        await update.message.reply_text(
            f"📊 **Estadísticas de {username}**\n\n"
            "🎮 ¡Aún no has jugado ningún mini-juego!\n\n"
            "**Comandos disponibles:**\n"
            "• `/cinematrivia` - Trivia cinematográfica\n"
            "• `/adivinapelicula` - Adivinar por pistas\n"
            "• `/emojipelicula` - Adivinar por emojis"
        )
        return
    
    # Calcular totales
    total_points = sum(stat[3] for stat in stats)
    total_correct = sum(stat[1] for stat in stats)
    total_attempts = sum(stat[2] for stat in stats)
    overall_accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
    
    stats_text = f"📊 **Estadísticas de {username}**\n\n"
    
    # Estadísticas generales
    stats_text += (
        f"🎯 **RESUMEN GENERAL**\n"
        f"🏆 **Puntos totales:** {total_points:,}\n"
        f"✅ **Aciertos:** {total_correct}/{total_attempts}\n"
        f"📈 **Precisión:** {overall_accuracy:.1f}%\n\n"
    )
    
    # Estadísticas por juego
    game_names = {
        'trivia': '🎬 Cine-Trivia',
        'guess_movie': '🔍 Adivina Película',
        'emoji_movie': '🎭 Emoji Película'
    }
    
    stats_text += "📋 **POR TIPO DE JUEGO**\n\n"
    
    for game_type, correct, attempts, points, current_streak, best_streak, last_played in stats:
        game_name = game_names.get(game_type, game_type.title())
        accuracy = (correct / attempts * 100) if attempts > 0 else 0
        
        # Formatear última vez jugado
        try:
            last_date = datetime.fromisoformat(last_played)
            last_formatted = last_date.strftime("%d/%m/%Y")
        except:
            last_formatted = "N/A"
        
        stats_text += (
            f"{game_name}\n"
            f"  🎯 {correct}/{attempts} ({accuracy:.1f}%)\n"
            f"  🏆 {points:,} puntos\n"
            f"  🔥 Racha: {current_streak} (mejor: {best_streak})\n"
            f"  📅 Último: {last_formatted}\n\n"
        )
    
    # Ranking personal (gamificación)
    if total_points >= 1000:
        rank = "🏆 Maestro del Cine"
    elif total_points >= 500:
        rank = "🥇 Experto Cinematográfico"
    elif total_points >= 200:
        rank = "🥈 Cinéfilo Avanzado"
    elif total_points >= 50:
        rank = "🥉 Aficionado al Cine"
    else:
        rank = "🎬 Principiante"
    
    stats_text += f"🎖️ **Rango actual:** {rank}"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def cmd_top_jugadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /topjugadores - Ranking global de jugadores"""
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    # Obtener top jugadores por puntos totales
    cursor.execute('''
        SELECT username, SUM(points_earned) as total_points, 
               SUM(correct_answers) as total_correct,
               SUM(total_attempts) as total_attempts,
               MAX(best_streak) as best_streak
        FROM game_stats 
        GROUP BY user_id, username
        HAVING total_points > 0
        ORDER BY total_points DESC
        LIMIT 10
    ''', ())
    
    top_players = cursor.fetchall()
    conn.close()
    
    if not top_players:
        await update.message.reply_text("📊 **Top Jugadores**\n\n🎮 ¡Aún no hay jugadores en el ranking!")
        return
    
    ranking_text = "🏆 **TOP 10 JUGADORES** 🎬\n\n"
    
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    
    for i, (username, points, correct, attempts, best_streak) in enumerate(top_players):
        position = i + 1
        medal = medals[i]
        accuracy = (correct / attempts * 100) if attempts > 0 else 0
        
        ranking_text += (
            f"{medal} **#{position} {username}**\n"
            f"    🏆 {points:,} puntos\n"
            f"    🎯 {accuracy:.1f}% precisión\n"
            f"    🔥 Mejor racha: {best_streak}\n\n"
        )
    
    await update.message.reply_text(ranking_text, parse_mode='Markdown')

# ========== MANEJADORES DE CALLBACKS MEJORADOS ==========

async def handle_trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar respuestas de trivia con mejores validaciones"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name or "Usuario"
    chat_id = query.message.chat_id
    
    # Parsear callback data
    try:
        parts = query.data.split('_')
        if parts[0] == "surrender" and parts[1] == "trivia":
            # Manejar rendición desde botón
            active_game = GameManager.get_active_game(chat_id, user_id, 'trivia')
            if active_game:
                GameManager.save_game_stats(user_id, username, 'trivia', False, 0)
                GameManager.end_active_game(chat_id, user_id, 'trivia')
                
                try:
                    game_info = json.loads(active_game[2])  # options field
                    correct_answer = active_game[1]  # correct_answer field
                    correct_option = next(opt for opt in game_info["options"] if opt.startswith(f"{correct_answer})"))
                    explanation = game_info.get('explanation', '')
                    
                    surrender_text = (
                        f"🏳️ **Te has rendido**\n\n"
                        f"✅ **Respuesta correcta:** {correct_option}\n"
                        f"📚 {explanation}\n\n"
                        f"💪 **¡Inténtalo de nuevo!**"
                    )
                except:
                    surrender_text = "🏳️ **Te has rendido**\n\n💪 **¡Inténtalo de nuevo!**"
                
                await query.edit_message_text(surrender_text, parse_mode='Markdown')
            return
        
        # Respuesta normal
        if len(parts) < 4:
            return
            
        _, correct_answer, user_answer, session_id = parts
        
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Error al procesar respuesta")
        return
    
    # Verificar juego activo
    active_game = GameManager.get_active_game(chat_id, user_id, 'trivia')
    if not active_game:
        await query.edit_message_text("❌ Este juego ya no está activo")
        return
    
    # Validar sesión (anti-trampa básico)
    expected_session = f"{chat_id}_{user_id}"
    if not session_id.startswith(expected_session):
        await query.edit_message_text("❌ Sesión inválida")
        return
    
    # Verificar respuesta
    is_correct = user_answer == correct_answer
    
    # Cargar datos de la pregunta
    try:
        question_data = json.loads(active_game[2])  # options field
        explanation = question_data.get('explanation', '')
        difficulty = question_data.get('difficulty', 'medium')
    except:
        explanation = ""
        difficulty = 'medium'
    
    # Calcular puntos (bonus por dificultad)
    points = TRIVIA_POINTS
    if is_correct:
        if difficulty == 'hard':
            points += 10
        elif difficulty == 'easy':
            points -= 5
        points = max(5, points)
    else:
        points = 0
    
    # Guardar estadísticas
    GameManager.save_game_stats(user_id, username, 'trivia', is_correct, points)
    
    # Terminar juego
    GameManager.end_active_game(chat_id, user_id, 'trivia')
    
    # Preparar respuesta
    if is_correct:
        result_emoji = "🎉"
        result_text = "¡CORRECTO!"
        color_emoji = "🟢"
    else:
        result_emoji = "❌"
        result_text = "INCORRECTO"
        color_emoji = "🔴"
    
    # Obtener respuesta correcta formateada
    try:
        correct_option = next(opt for opt in question_data["options"] if opt.startswith(f"{correct_answer})"))
    except:
        correct_option = f"Opción {correct_answer}"
    
    response_text = (
        f"{result_emoji} **{result_text}**\n\n"
        f"✅ **Respuesta correcta:** {correct_option}\n"
    )
    
    if explanation:
        response_text += f"📚 **Explicación:** {explanation}\n"
    
    response_text += (
        f"\n🏆 **Puntos obtenidos:** +{points}\n"
        f"{color_emoji} **Dificultad:** {difficulty.title()}"
    )
    
    if is_correct:
        response_text += "\n\n🎬 **¡Sigue así, cinéfilo!**"
    else:
        response_text += "\n\n💪 **¡La próxima será!**"
    
    await query.edit_message_text(response_text, parse_mode='Markdown')

async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar respuestas de texto para juegos de adivinanza mejorado"""
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "Usuario"
    chat_id = update.effective_chat.id
    user_answer = update.message.text.strip()
    
    # Verificar juegos activos de adivinanza
    guess_game = GameManager.get_active_game(chat_id, user_id, 'guess_movie')
    emoji_game = GameManager.get_active_game(chat_id, user_id, 'emoji_movie')
    
    if not guess_game and not emoji_game:
        return  # No hay juegos activos, no hacer nada
    
    # Determinar tipo de juego
    if guess_game:
        game_type = 'guess_movie'
        active_game = guess_game
        base_points = GUESS_MOVIE_BASE_POINTS
        penalty_per_hint = GUESS_MOVIE_HINT_PENALTY
    else:
        game_type = 'emoji_movie'
        active_game = emoji_game
        base_points = EMOJI_MOVIE_POINTS
        penalty_per_hint = 0  # Sin penalización por pistas en emoji
    
    # Extraer datos del juego
    current_question, correct_answers_json, options, attempts, hints_used, max_hints, points_available, expires_at = active_game
    
    try:
        correct_answers = json.loads(correct_answers_json)
        game_data = json.loads(options)
    except:
        await update.message.reply_text("❌ Error al cargar datos del juego")
        return
    
    # Normalizar respuestas para comparación
    normalized_user_answer = GameManager.normalize_answer(user_answer)
    normalized_correct_answers = [GameManager.normalize_answer(ans) for ans in correct_answers]
    
    # Verificar si la respuesta es correcta
    is_correct = any(normalized_user_answer in correct_ans or correct_ans in normalized_user_answer 
                    for correct_ans in normalized_correct_answers)
    
    # Calcular puntos
    if is_correct:
        penalty = penalty_per_hint * hints_used
        points = max(5, base_points - penalty)
    else:
        points = 0
    
    # Actualizar intentos
    GameManager.update_game_attempts(chat_id, user_id, game_type)
    
    # Guardar estadísticas
    GameManager.save_game_stats(user_id, username, game_type, is_correct, points)
    
    # Terminar juego
    GameManager.end_active_game(chat_id, user_id, game_type)
    
    # Preparar respuesta
    if is_correct:
        result_emoji = "🎉"
        result_text = "¡CORRECTO!"
        
        bonus_text = ""
        if hints_used == 0:
            bonus_text = "\n🌟 **¡Perfecto sin pistas!**"
        elif hints_used == 1:
            bonus_text = "\n👏 **¡Muy bien con solo una pista!**"
        
        response_text = (
            f"{result_emoji} **{result_text}**\n\n"
            f"🎬 **Película:** {game_data['title']}\n"
            f"💭 **Tu respuesta:** {user_answer}\n"
            f"🏆 **Puntos obtenidos:** +{points}\n"
            f"💡 **Pistas usadas:** {hints_used}/{max_hints}"
            f"{bonus_text}\n\n"
            f"🎭 **¡Excelente conocimiento cinematográfico!**"
        )
    else:
        response_text = (
            f"❌ **INCORRECTO**\n\n"
            f"🎬 **Película:** {game_data['title']}\n"
            f"💭 **Tu respuesta:** {user_answer}\n"
            f"✅ **Respuestas válidas:** {', '.join(correct_answers[:3])}\n"
            f"💡 **Pistas usadas:** {hints_used}/{max_hints}\n\n"
            f"💪 **¡Sigue intentando, cada vez estarás más cerca!**"
        )
    
    await update.message.reply_text(response_text, parse_mode='Markdown')

# ========== INICIALIZACIÓN Y LIMPIEZA AUTOMÁTICA ==========

async def cleanup_games_periodically():
    """Limpiar juegos expirados periódicamente"""
    while True:
        try:
            GameManager.cleanup_expired_games()
            await asyncio.sleep(3600)  # Cada hora
        except Exception as e:
            logger.error(f"Error en limpieza automática: {e}")
            await asyncio.sleep(3600)

def initialize_games_system():
    """Inicializar el sistema de mini-juegos"""
    try:
        create_games_tables()
        logger.info("🎮 Sistema de mini-juegos inicializado correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al inicializar sistema de juegos: {e}")
        return False

# ========== COMANDOS ADICIONALES DE UTILIDAD ==========

async def cmd_limpiar_juegos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para limpiar juegos activos del usuario (útil para debugging)"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Limpiar todos los juegos activos del usuario
    games_cleared = 0
    for game_type in ['trivia', 'guess_movie', 'emoji_movie']:
        if GameManager.end_active_game(chat_id, user_id, game_type):
            games_cleared += 1
    
    if games_cleared > 0:
        await update.message.reply_text(
            f"🧹 **Limpieza completada**\n\n"
            f"Se terminaron {games_cleared} juego(s) activo(s)\n"
            f"Ya puedes iniciar nuevos juegos"
        )
    else:
        await update.message.reply_text("✨ No tienes juegos activos para limpiar")

async def cmd_ayuda_juegos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de ayuda específico para mini-juegos"""
    help_text = (
        "🎮 **GUÍA DE MINI-JUEGOS** 🎬\n\n"
        
        "**🎯 CINE-TRIVIA**\n"
        "• Comando: `/cinematrivia`\n"
        "• Responde preguntas de cine\n"
        "• +25 puntos base (+bonus por dificultad)\n"
        "• 60 segundos para responder\n\n"
        
        "**🔍 ADIVINA LA PELÍCULA**\n"
        "• Comando: `/adivinapelicula`\n"
        "• Adivina por pistas progresivas\n"
        "• +30 puntos base (-5 por cada pista)\n"
        "• Usa `/pista` para más ayuda\n\n"
        
        "**🎭 PELÍCULA EN EMOJIS**\n"
        "• Comando: `/emojipelicula`\n"
        "• Interpreta emojis para adivinar\n"
        "• +20 puntos por respuesta correcta\n"
        "• `/pista` revela el título exacto\n\n"
        
        "**📊 COMANDOS ÚTILES**\n"
        "• `/estadisticasjuegos` - Tus estadísticas\n"
        "• `/topjugadores` - Ranking global\n"
        "• `/pista` - Pedir ayuda en adivinanzas\n"
        "• `/rendirse` - Terminar juego actual\n"
        "• `/limpiarjuegos` - Limpiar juegos activos\n\n"
        
        "**🏆 SISTEMA DE PUNTOS**\n"
        "• Acumula puntos por respuestas correctas\n"
        "• Mantén rachas para mejor ranking\n"
        "• Dificultad afecta puntuación\n"
        "• Compite en el ranking global\n\n"
        
        "**💡 CONSEJOS**\n"
        "• Solo puedes tener un juego activo por tipo\n"
        "• Los juegos expiran en 1 hora\n"
        "• Las pistas reducen puntos en adivinanzas\n"
        "• ¡Practica para mejorar tu ranking!"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ========== EXPORTAR FUNCIONES PRINCIPALES ==========

# Funciones que deben ser importadas y registradas en el bot principal
GAME_COMMANDS = {
    'cinematrivia': cmd_cinematrivia,
    'adivinapelicula': cmd_adivinapelicula,  
    'emojipelicula': cmd_emojipelicula,
    'pista': cmd_pista,
    'rendirse': cmd_rendirse,
    'estadisticasjuegos': cmd_estadisticas_juegos,
    'topjugadores': cmd_top_jugadores,
    'limpiarjuegos': cmd_limpiar_juegos,
    'ayudajuegos': cmd_ayuda_juegos
}

GAME_HANDLERS = {
    'trivia_callback': handle_trivia_callback,
    'game_message': handle_game_message,
    'cleanup_periodic': cleanup_games_periodically
}

# Función de inicialización que debe llamarse al iniciar el bot
def setup_games_system():
    """Configurar el sistema completo de mini-juegos"""
    if initialize_games_system():
        logger.info("🎮 ¡Sistema de mini-juegos listo para usar!")
        return True
    else:
        logger.error("❌ Error al configurar sistema de mini-juegos")
        return False
