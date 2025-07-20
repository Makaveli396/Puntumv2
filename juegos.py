
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import add_points

# Almacenamiento de juegos activos (en memoria)
active_games = {}
game_stats = {}

# Datos de ejemplo para juegos
MOVIES_TRIVIA = [
    {
        "question": "¿Quién dirigió la película 'Inception' (2010)?",
        "options": ["Christopher Nolan", "Denis Villeneuve", "Ridley Scott", "David Fincher"],
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
        "question": "¿Cuál de estas películas ganó el Oscar a Mejor Película en 2020?",
        "options": ["1917", "Joker", "Parasite", "Once Upon a Time in Hollywood"],
        "correct": 2,
        "points": 12
    },
    {
        "question": "¿Quién interpretó a Neo en 'The Matrix'?",
        "options": ["Will Smith", "Keanu Reeves", "Tom Cruise", "Leonardo DiCaprio"],
        "correct": 1,
        "points": 8
    },
    {
        "question": "¿Cuál es la película más taquillera de todos los tiempos (sin ajustar por inflación)?",
        "options": ["Titanic", "Avatar", "Avengers: Endgame", "Star Wars"],
        "correct": 2,
        "points": 15
    },
    {
        "question": "¿Qué director es conocido por películas como 'The Shining' y '2001: A Space Odyssey'?",
        "options": ["Steven Spielberg", "Martin Scorsese", "Stanley Kubrick", "Francis Ford Coppola"],
        "correct": 2,
        "points": 12
    }
]

GUESS_MOVIES = [
    {
        "title": "El Padrino",
        "clues": [
            "Una saga familiar en Nueva York",
            "Marlon Brando interpreta al patriarca",
            "Francis Ford Coppola la dirigió",
            "La propuesta que no puedes rechazar"
        ],
        "points": 15
    },
    {
        "title": "Titanic",
        "clues": [
            "Un barco famoso",
            "Leonardo DiCaprio y Kate Winslet",
            "James Cameron dirigió",
            "Romance en alta mar que termina mal"
        ],
        "points": 12
    },
    {
        "title": "Star Wars",
        "clues": [
            "Guerra en las galaxias",
            "Luke, Leia y Han Solo",
            "George Lucas creó esta saga",
            "Que la fuerza te acompañe"
        ],
        "points": 10
    },
    {
        "title": "Pulp Fiction",
        "clues": [
            "Película no lineal de los 90",
            "John Travolta y Samuel L. Jackson",
            "Quentin Tarantino la dirigió",
            "Royale con queso"
        ],
        "points": 18
    },
    {
        "title": "Forrest Gump",
        "clues": [
            "La vida es como una caja de chocolates",
            "Tom Hanks corre por América",
            "Robert Zemeckis dirigió",
            "Ping pong y camarones"
        ],
        "points": 14
    }
]

EMOJI_MOVIES = [
    {"emojis": "👑🦁", "title": "El Rey León", "points": 8},
    {"emojis": "🚗⚡", "title": "Cars", "points": 6},
    {"emojis": "🕷️🕸️", "title": "Spider-Man", "points": 7},
    {"emojis": "🧙‍♂️⚡", "title": "Harry Potter", "points": 9},
    {"emojis": "🐠🔍", "title": "Finding Nemo", "points": 8},
    {"emojis": "❄️⛄", "title": "Frozen", "points": 6},
    {"emojis": "🦖🏝️", "title": "Jurassic Park", "points": 10},
    {"emojis": "👻🏠", "title": "Casper", "points": 7},
    {"emojis": "🤖🚀", "title": "Wall-E", "points": 9},
    {"emojis": "🐭🏰", "title": "Mickey Mouse", "points": 5},
    {"emojis": "🦸‍♂️🛡️", "title": "Capitán América", "points": 8},
    {"emojis": "🚢❄️", "title": "Titanic", "points": 12},
    {"emojis": "🍫🏭", "title": "Charlie y la Fábrica de Chocolate", "points": 11},
    {"emojis": "🐧🕺", "title": "Happy Feet", "points": 9},
    {"emojis": "👽🏠", "title": "E.T.", "points": 10}
]

# Nuevos juegos añadidos
DIRECTOR_GUESS = [
    {
        "director": "Christopher Nolan",
        "movies": ["Inception", "The Dark Knight", "Interstellar", "Dunkirk"],
        "clues": [
            "Maestro de los plots complejos y no lineales",
            "Le fascina el tiempo y los sueños",
            "Dirigió la trilogía de Batman con Christian Bale",
            "Inception y Interstellar son sus obras maestras"
        ],
        "points": 15
    },
    {
        "director": "Quentin Tarantino",
        "movies": ["Pulp Fiction", "Kill Bill", "Django Unchained", "Inglourious Basterds"],
        "clues": [
            "Famoso por sus diálogos únicos",
            "Le encanta la violencia estilizada",
            "Suele aparecer en cameos en sus películas",
            "Royale con queso y pies descalzos"
        ],
        "points": 12
    },
    {
        "director": "Steven Spielberg",
        "movies": ["Jaws", "E.T.", "Jurassic Park", "Schindler's List"],
        "clues": [
            "Pionero del blockbuster moderno",
            "Creó dinosaurios que parecían reales",
            "También dirigió dramas históricos",
            "Tiburón y extraterrestre amigable"
        ],
        "points": 10
    }
]

MOVIE_QUOTES = [
    {"quote": "Que la fuerza te acompañe", "movie": "Star Wars", "points": 8},
    {"quote": "Hasta la vista, baby", "movie": "Terminator 2", "points": 10},
    {"quote": "Frankly, my dear, I don't give a damn", "movie": "Gone with the Wind", "points": 15},
    {"quote": "I'll be back", "movie": "Terminator", "points": 7},
    {"quote": "Here's looking at you, kid", "movie": "Casablanca", "points": 12},
    {"quote": "Show me the money!", "movie": "Jerry Maguire", "points": 9},
    {"quote": "Houston, we have a problem", "movie": "Apollo 13", "points": 11},
    {"quote": "Keep your friends close, but your enemies closer", "movie": "The Godfather Part II", "points": 14}
]

def initialize_games_system():
    """Inicializar el sistema de juegos"""
    print("[INFO] ✅ Sistema de juegos inicializado")
    return True

async def cleanup_games_periodically():
    """Limpiar juegos inactivos cada hora"""
    while True:
        try:
            current_time = datetime.now()
            games_to_remove = []
            
            for key, game in active_games.items():
                if current_time - game.get('started_at', current_time) > timedelta(hours=1):
                    games_to_remove.append(key)
            
            for key in games_to_remove:
                del active_games[key]
            
            if games_to_remove:
                print(f"[INFO] Limpiados {len(games_to_remove)} juegos inactivos")
            
    await _auto_async_func_1(update, context)
            
        except Exception as e:
            print(f"[ERROR] Error en limpieza de juegos: {e}")
    await _auto_async_func_2(update, context)

def get_game_key(chat_id: int, user_id: int) -> str:
    """Generar clave única para el juego"""
    return f"{chat_id}_{user_id}"

def update_game_stats(user_id: int, game_type: str, result: str):
    """Actualizar estadísticas de juegos del usuario"""
    if user_id not in game_stats:
        game_stats[user_id] = {}
    
    if game_type not in game_stats[user_id]:
        game_stats[user_id][game_type] = {"wins": 0, "losses": 0, "total": 0}
    
    game_stats[user_id][game_type]["total"] += 1
    if result == "win":
        game_stats[user_id][game_type]["wins"] += 1
    else:
        game_stats[user_id][game_type]["losses"] += 1

# =================== CINEMATRIVIA ===================
async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iniciar trivia de cine"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_3(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    question = random.choice(MOVIES_TRIVIA)
    
    active_games[game_key] = {
        "type": "trivia",
        "question": question,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    keyboard = []
    for i, option in enumerate(question["options"]):
        keyboard.append([InlineKeyboardButton(
            f"{chr(65+i)}. {option}", 
            callback_data=f"trivia_{game_key}_{i}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    trivia_text = f"""
🎬 **CINEMATRIVIA** 🍿

**Pregunta:**
{question['question']}

**Puntos en juego:** {question['points']} 💎

Selecciona tu respuesta:
    """
    
    await _auto_async_func_4(update, context)
        trivia_text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar respuestas de trivia"""
    query = update.callback_query
    await _auto_async_func_5(update, context)
    
    try:
        _, game_key, answer = query.data.split('_', 2)
        answer = int(answer)
    except (ValueError, IndexError):
    await _auto_async_func_6(update, context)
        return
    
    if game_key not in active_games:
    await _auto_async_func_7(update, context)
        return
    
    game = active_games[game_key]
    question = game["question"]
    user = query.from_user
    
    if answer == question["correct"]:
        points = question["points"]
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=points,
            hashtag="(cinematrivia)",
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            context=context
        )
        
        result_text = f"""
✅ **¡CORRECTO!** 🎉

👤 {user.mention_html()}
🎯 Respuesta: **{question['options'][answer]}**
💎 **+{points} puntos ganados**

¡Excelente conocimiento cinematográfico! 🍿
        """
        update_game_stats(user.id, "trivia", "win")
        
    else:
        correct_answer = question["options"][question["correct"]]
        result_text = f"""
❌ **Respuesta incorrecta** 😔

👤 {user.mention_html()}
🎯 Tu respuesta: {question['options'][answer]}
✅ Respuesta correcta: **{correct_answer}**

¡Sigue intentando! 🎬
        """
        update_game_stats(user.id, "trivia", "loss")
    
    await _auto_async_func_8(update, context)
    del active_games[game_key]

# =================== ADIVINA PELÍCULA ===================
async def cmd_adivinapelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar película por pistas"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_9(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    movie = random.choice(GUESS_MOVIES)
    
    active_games[game_key] = {
        "type": "guess_movie",
        "movie": movie,
        "current_clue": 0,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    game_text = f"""
🎬 **ADIVINA LA PELÍCULA** 🔍

💡 **Pista 1/4:**
{movie['clues'][0]}

**Puntos en juego:** {movie['points']} 💎
*(Los puntos disminuyen con cada pista)*

**¿Cuál es la película?**
Responde con el nombre de la película.

💡 Usa /pista para obtener la siguiente pista
🚪 Usa /rendirse para abandonar
    """
    
    await _auto_async_func_10(update, context)

async def cmd_pista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dar siguiente pista en el juego de adivinar película"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key not in active_games:
    await _auto_async_func_11(update, context)
        return
    
    game = active_games[game_key]
    
    if game["type"] not in ["guess_movie", "guess_director"]:
    await _auto_async_func_12(update, context)
        return
    
    if game["current_clue"] >= 3:
    await _auto_async_func_13(update, context)
        return
    
    game["current_clue"] += 1
    current_clue = game["current_clue"]
    
    if game["type"] == "guess_movie":
        movie = game["movie"]
        points_remaining = max(movie["points"] - (current_clue * 3), 3)
        
        pista_text = f"""
🎬 **ADIVINA LA PELÍCULA** 🔍

💡 **Pista {current_clue + 1}/4:**
{movie['clues'][current_clue]}

**Puntos restantes:** {points_remaining} 💎

**¿Cuál es la película?**
Responde con el nombre de la película.
        """
        
    elif game["type"] == "guess_director":
        director = game["director"]
        points_remaining = max(director["points"] - (current_clue * 3), 3)
        
        pista_text = f"""
🎬 **ADIVINA EL DIRECTOR** 🎭

💡 **Pista {current_clue + 1}/4:**
{director['clues'][current_clue]}

**Puntos restantes:** {points_remaining} 💎

**¿Quién es el director?**
Responde con el nombre del director.
        """
    
    if current_clue < 3:
        pista_text += "\n💡 Usa /pista para obtener la siguiente pista"
    
    pista_text += "\n🚪 Usa /rendirse para abandonar"
    
    await _auto_async_func_14(update, context)

# =================== EMOJI PELÍCULA ===================
async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar película por emojis"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_15(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    movie = random.choice(EMOJI_MOVIES)
    
    active_games[game_key] = {
        "type": "emoji_movie",
        "movie": movie,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    emoji_text = f"""
🎬 **EMOJI PELÍCULA** 🎭

**Adivina la película:**
{movie['emojis']}

**Puntos en juego:** {movie['points']} 💎

**¿Cuál es la película?**
Responde con el nombre de la película.

🚪 Usa /rendirse para abandonar
    """
    
    await _auto_async_func_16(update, context)

# =================== ADIVINA DIRECTOR ===================
async def cmd_adivinadirector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar director por pistas"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_17(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    director_data = random.choice(DIRECTOR_GUESS)
    
    active_games[game_key] = {
        "type": "guess_director",
        "director": director_data,
        "current_clue": 0,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    director_text = f"""
🎬 **ADIVINA EL DIRECTOR** 🎭

**Películas famosas:**
• {director_data['movies'][0]}
• {director_data['movies'][1]}
• {director_data['movies'][2]}

💡 **Pista 1/4:**
{director_data['clues'][0]}

**Puntos en juego:** {director_data['points']} 💎

**¿Quién es el director?**
Responde con el nombre del director.

💡 Usa /pista para obtener la siguiente pista
🚪 Usa /rendirse para abandonar
    """
    
    await _auto_async_func_18(update, context)

# =================== ADIVINA FRASE ===================
async def cmd_adivinafrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar película por frase famosa"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_19(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    quote_data = random.choice(MOVIE_QUOTES)
    
    active_games[game_key] = {
        "type": "guess_quote",
        "quote": quote_data,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    quote_text = f"""
🎬 **ADIVINA LA PELÍCULA POR LA FRASE** 🎭

**Frase famosa:**
*"{quote_data['quote']}"*

**Puntos en juego:** {quote_data['points']} 💎

**¿De qué película es esta frase?**
Responde con el nombre de la película.

🚪 Usa /rendirse para abandonar
    """
    
    await _auto_async_func_20(update, context)

# =================== RENDERIRSE ===================
async def cmd_rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rendirse del juego actual"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key not in active_games:
    await _auto_async_func_21(update, context)
        return
    
    game = active_games[game_key]
    game_type = game["type"]
    
    # Obtener respuesta correcta según tipo de juego
    if game_type == "trivia":
        correct = game["question"]["options"][game["question"]["correct"]]
        response_text = f"🏳️ Te has rendido.\n✅ La respuesta era: **{correct}**"
    elif game_type == "guess_movie":
        correct = game["movie"]["title"]
        response_text = f"🏳️ Te has rendido.\n🎬 La película era: **{correct}**"
    elif game_type == "emoji_movie":
        correct = game["movie"]["title"]
        response_text = f"🏳️ Te has rendido.\n🎬 La película era: **{correct}**"
    elif game_type == "guess_director":
        correct = game["director"]["director"]
        response_text = f"🏳️ Te has rendido.\n🎭 El director era: **{correct}**"
    elif game_type == "guess_quote":
        correct = game["quote"]["movie"]
        response_text = f"🏳️ Te has rendido.\n🎬 La película era: **{correct}**"
    else:
        response_text = "🏳️ Te has rendido del juego actual."
    
    # Actualizar estadísticas
    update_game_stats(user.id, game_type, "loss")
    
    # Eliminar juego
    del active_games[game_key]
    
    response_text += "\n\n¡Inténtalo de nuevo cuando quieras! 🎮"
    await _auto_async_func_22(update, context)

# =================== ESTADÍSTICAS DE JUEGOS ===================
async def cmd_estadisticasjuegos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver estadísticas personales de juegos"""
    user = update.effective_user
    
    if user.id not in game_stats:
    await _auto_async_func_23(update, context)
            "📊 Aún no tienes estadísticas de juegos.\n"
            "¡Juega algunos juegos para ver tus stats!"
        )
        return
    
    user_stats = game_stats[user.id]
    stats_text = f"🎮 **ESTADÍSTICAS DE JUEGOS - {user.first_name}**\n\n"
    
    game_names = {
        "trivia": "🎬 Cinematrivia",
        "guess_movie": "🔍 Adivina Película",
        "emoji_movie": "🎭 Emoji Película",
        "guess_director": "🎭 Adivina Director", 
        "guess_quote": "💬 Adivina Frase"
    }
    
    total_wins = total_losses = total_games = 0
    
    for game_type, stats in user_stats.items():
        if game_type in game_names:
            wins = stats["wins"]
            losses = stats["losses"]
            total = stats["total"]
            win_rate = (wins / total * 100) if total > 0 else 0
            
            total_wins += wins
            total_losses += losses
            total_games += total
            
            stats_text += f"{game_names[game_type]}:\n"
            stats_text += f"   🏆 Victorias: {wins}\n"
            stats_text += f"   💔 Derrotas: {losses}\n"
            stats_text += f"   📊 Win Rate: {win_rate:.1f}%\n\n"
    
    # Estadísticas generales
    overall_win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    stats_text += "📈 **TOTALES:**\n"
    stats_text += f"🎯 Juegos jugados: {total_games}\n"
    stats_text += f"🏆 Victorias totales: {total_wins}\n"
    stats_text += f"📊 Win Rate general: {overall_win_rate:.1f}%\n"
    
    await _auto_async_func_24(update, context)

# =================== TOP JUGADORES ===================
async def cmd_top_jugadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver ranking global de jugadores de juegos"""
    if not game_stats:
    await _auto_async_func_25(update, context)
            "📊 Aún no hay estadísticas de juegos.\n"
            "¡Sean los primeros en jugar!"
        )
        return
    
    # Calcular ranking por victorias totales
    player_rankings = []
    
    for user_id, user_data in game_stats.items():
        total_wins = 0
        total_games = 0
        
        for game_type, stats in user_data.items():
            total_wins += stats.get("wins", 0)
            total_games += stats.get("total", 0)
        
        if total_games > 0:
            win_rate = (total_wins / total_games * 100)
            player_rankings.append({
                "user_id": user_id,
                "wins": total_wins,
                "games": total_games,
                "win_rate": win_rate
            })
    
    # Ordenar por victorias (y win rate como criterio secundario)
    player_rankings.sort(key=lambda x: (x["wins"], x["win_rate"]), reverse=True)
    
    if not player_rankings:
    await _auto_async_func_26(update, context)
        return
    
    ranking_text = "🏆 **TOP JUGADORES - RANKING GLOBAL** 🎮\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, player in enumerate(player_rankings[:10]):  # Top 10
        if i < 3:
            medal = medals[i]
        else:
            medal = f"{i+1}."
        
        # Obtener información del usuario (necesitarías almacenar nombres)
        # Por ahora usamos el user_id
        ranking_text += f"{medal} **Usuario {player['user_id']}**\n"
        ranking_text += f"   🏆 Victorias: {player['wins']}\n"
        ranking_text += f"   🎯 Juegos: {player['games']}\n"
        ranking_text += f"   📊 Win Rate: {player['win_rate']:.1f}%\n\n"
    
    ranking_text += "🎬 ¡Sigue jugando para subir en el ranking!"
    
    await _auto_async_func_27(update, context)

# =================== MANEJO DE RESPUESTAS DE JUEGOS ===================
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar respuestas de texto en juegos activos"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    message_text = update.message.text.lower().strip()
    
    if game_key not in active_games:
        return False  # No hay juego activo
    
    game = active_games[game_key]
    game_type = game["type"]
    
    # Verificar respuesta según tipo de juego
correct = False
correct_answer = ""
points = 0

if game_type == "guess_movie":
    correct_answer = game["movie"]["title"]
    points = max(game["movie"]["points"] - (game["current_clue"] * 3), 3)
    correct = is_similar_answer(message_text, correct_answer)

elif game_type == "emoji_movie":
    correct_answer = game["movie"]["title"]
    points = game["movie"]["points"]
    correct = is_similar_answer(message_text, correct_answer)

elif game_type == "guess_director":
    correct_answer = game["director"]["director"]
    points = max(game["director"]["points"] - (game["current_clue"] * 3), 3)
    correct = is_similar_answer(message_text, correct_answer)

elif game_type == "guess_quote":
    correct_answer = game["quote"]["quote"]
    points = game["quote"]["points"]
    correct = is_similar_answer(message_text, correct_answer)

else:
    correct_answer = ""
    points = 0
    correct = False


    
    # Procesar resultado
    if correct:
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=points,
            hashtag=f"({game_type})",
            chat_id=chat.id,
            message_id=update.message.message_id,
            context=context
        )
        
        result_text = f"""
✅ **¡CORRECTO!** 🎉

👤 {user.mention_html()}
🎯 Respuesta: **{correct_answer}**
💎 **+{points} puntos ganados**

¡Excelente conocimiento cinematográfico! 🍿
        """
        update_game_stats(user.id, game_type, "win")
        
    await _auto_async_func_28(update, context)
        del active_games[game_key]
        return True
        
    else:
        # Respuesta incorrecta - el juego continúa
    await _auto_async_func_29(update, context)
            f"❌ No es correcto. ¡Sigue intentando!\n"
            f"💡 Usa /pista para más ayuda (si está disponible)\n"
            f"🚪 Usa /rendirse para abandonar"
        )
        return True

def is_similar_answer(user_answer: str, correct_answer: str) -> bool:
    """Verificar si la respuesta del usuario es similar a la correcta"""
    import re
    
    # Limpiar y normalizar respuestas
    def normalize_text(text):
        # Convertir a minúsculas y quitar acentos básicos
        text = text.lower()
        text = text.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        text = text.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
        # Quitar caracteres especiales y espacios extra
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        return text
    
    user_normalized = normalize_text(user_answer)
    correct_normalized = normalize_text(correct_answer)
    
    # Verificaciones de similitud
    # 1. Coincidencia exacta
    if user_normalized == correct_normalized:
        return True
    
    # 2. El usuario escribió la respuesta correcta dentro de su mensaje
    if correct_normalized in user_normalized:
        return True
    
    # 3. Palabras clave importantes (para títulos largos)
    user_words = set(user_normalized.split())
    correct_words = set(correct_normalized.split())
    
    # Si hay al menos 2 palabras importantes en común y el título no es muy corto
    if len(correct_words) > 1:
        common_words = user_words.intersection(correct_words)
        important_words = correct_words - {'the', 'el', 'la', 'los', 'las', 'de', 'del', 'y', 'and', 'of', 'in', 'a', 'an'}
        
        if len(common_words) >= min(2, len(important_words)):
            return True
    
    # 4. Para nombres de directores (nombre y apellido)
    if len(correct_normalized.split()) >= 2:
        # Si el usuario mencionó al menos el apellido
        correct_parts = correct_normalized.split()
        if any(part in user_normalized for part in correct_parts if len(part) > 3):
            return True
    
    return False

# =================== COMANDOS DE AYUDA ===================
async def cmd_juegos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar todos los juegos disponibles"""
    games_text = """
🎮 **JUEGOS DE CINE DISPONIBLES** 🎬

🎯 **JUEGOS DE TRIVIA:**
• `/cinematrivia` - Preguntas de opción múltiple
• `/adivinafrase` - Adivina la película por una frase famosa

🔍 **JUEGOS DE ADIVINANZA:**
• `/adivinapelicula` - Adivina película por pistas
• `/adivinadirector` - Adivina director por pistas  
• `/emojipelicula` - Adivina película por emojis

⚡ **COMANDOS ÚTILES:**
• `/pista` - Obtener siguiente pista (juegos con pistas)
• `/rendirse` - Abandonar juego actual
• `/estadisticasjuegos` - Ver tus estadísticas
• `/topjugadores` - Ver ranking global

🎯 **¿Cómo jugar?**
1. Usa cualquier comando de juego para empezar
2. Solo puedes tener un juego activo a la vez
3. Ganas puntos por respuestas correctas
4. ¡Entre menos pistas uses, más puntos ganas!

🏆 **Sistema de puntos:**
- Respuestas correctas = Puntos para el ranking
- Los puntos varían según la dificultad
- Usa menos pistas para maximizar puntos

¡Demuestra tu conocimiento cinematográfico! 🍿
    """
    
    await _auto_async_func_30(update, context)

# =================== EXPORTAR FUNCIONES ===================
def get_game_handlers():
    """Retornar todos los handlers de juegos para registrar en main.py"""
    return {
        'commands': [
            ('cinematrivia', cmd_cinematrivia),
            ('adivinapelicula', cmd_adivinapelicula),
            ('emojipelicula', cmd_emojipelicula),
            ('adivinadirector', cmd_adivinadirector),
            ('adivinafrase', cmd_adivinafrase),
            ('pista', cmd_pista),
            ('rendirse', cmd_rendirse),
            ('estadisticasjuegos', cmd_estadisticasjuegos),
            ('topjugadores', cmd_top_jugadores),
            ('juegos', cmd_juegos)
        ],
        'callbacks': [
            ('trivia_', handle_trivia_callback)
        ],
        'message_handler': handle_game_message
    }
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import add_points
# Almacenamiento de juegos activos (en memoria)
active_games = {}
game_stats = {}

# Datos de ejemplo para juegos
MOVIES_TRIVIA = [
    {
        "question": "¿Quién dirigió la película 'Inception' (2010)?",
        "options": ["Christopher Nolan", "Denis Villeneuve", "Ridley Scott", "David Fincher"],
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
        "question": "¿Cuál de estas películas ganó el Oscar a Mejor Película en 2020?",
        "options": ["1917", "Joker", "Parasite", "Once Upon a Time in Hollywood"],
        "correct": 2,
        "points": 12
    },
    {
        "question": "¿Quién interpretó a Neo en 'The Matrix'?",
        "options": ["Will Smith", "Keanu Reeves", "Tom Cruise", "Leonardo DiCaprio"],
        "correct": 1,
        "points": 8
    },
    {
        "question": "¿Cuál es la película más taquillera de todos los tiempos (sin ajustar por inflación)?",
        "options": ["Titanic", "Avatar", "Avengers: Endgame", "Star Wars"],
        "correct": 2,
        "points": 15
    },
    {
        "question": "¿Qué director es conocido por películas como 'The Shining' y '2001: A Space Odyssey'?",
        "options": ["Steven Spielberg", "Martin Scorsese", "Stanley Kubrick", "Francis Ford Coppola"],
        "correct": 2,
        "points": 12
    }
]

GUESS_MOVIES = [
    {
        "title": "El Padrino",
        "clues": [
            "Una saga familiar en Nueva York",
            "Marlon Brando interpreta al patriarca",
            "Francis Ford Coppola la dirigió",
            "La propuesta que no puedes rechazar"
        ],
        "points": 15
    },
    {
        "title": "Titanic",
        "clues": [
            "Un barco famoso",
            "Leonardo DiCaprio y Kate Winslet",
            "James Cameron dirigió",
            "Romance en alta mar que termina mal"
        ],
        "points": 12
    },
    {
        "title": "Star Wars",
        "clues": [
            "Guerra en las galaxias",
            "Luke, Leia y Han Solo",
            "George Lucas creó esta saga",
            "Que la fuerza te acompañe"
        ],
        "points": 10
    },
    {
        "title": "Pulp Fiction",
        "clues": [
            "Película no lineal de los 90",
            "John Travolta y Samuel L. Jackson",
            "Quentin Tarantino la dirigió",
            "Royale con queso"
        ],
        "points": 18
    },
    {
        "title": "Forrest Gump",
        "clues": [
            "La vida es como una caja de chocolates",
            "Tom Hanks corre por América",
            "Robert Zemeckis dirigió",
            "Ping pong y camarones"
        ],
        "points": 14
    }
]

EMOJI_MOVIES = [
    {"emojis": "👑🦁", "title": "El Rey León", "points": 8},
    {"emojis": "🚗⚡", "title": "Cars", "points": 6},
    {"emojis": "🕷️🕸️", "title": "Spider-Man", "points": 7},
    {"emojis": "🧙‍♂️⚡", "title": "Harry Potter", "points": 9},
    {"emojis": "🐠🔍", "title": "Finding Nemo", "points": 8},
    {"emojis": "❄️⛄", "title": "Frozen", "points": 6},
    {"emojis": "🦖🏝️", "title": "Jurassic Park", "points": 10},
    {"emojis": "👻🏠", "title": "Casper", "points": 7},
    {"emojis": "🤖🚀", "title": "Wall-E", "points": 9},
    {"emojis": "🐭🏰", "title": "Mickey Mouse", "points": 5},
    {"emojis": "🦸‍♂️🛡️", "title": "Capitán América", "points": 8},
    {"emojis": "🚢❄️", "title": "Titanic", "points": 12},
    {"emojis": "🍫🏭", "title": "Charlie y la Fábrica de Chocolate", "points": 11},
    {"emojis": "🐧🕺", "title": "Happy Feet", "points": 9},
    {"emojis": "👽🏠", "title": "E.T.", "points": 10}
]

# Nuevos juegos añadidos
DIRECTOR_GUESS = [
    {
        "director": "Christopher Nolan",
        "movies": ["Inception", "The Dark Knight", "Interstellar", "Dunkirk"],
        "clues": [
            "Maestro de los plots complejos y no lineales",
            "Le fascina el tiempo y los sueños",
            "Dirigió la trilogía de Batman con Christian Bale",
            "Inception y Interstellar son sus obras maestras"
        ],
        "points": 15
    },
    {
        "director": "Quentin Tarantino",
        "movies": ["Pulp Fiction", "Kill Bill", "Django Unchained", "Inglourious Basterds"],
        "clues": [
            "Famoso por sus diálogos únicos",
            "Le encanta la violencia estilizada",
            "Suele aparecer en cameos en sus películas",
            "Royale con queso y pies descalzos"
        ],
        "points": 12
    },
    {
        "director": "Steven Spielberg",
        "movies": ["Jaws", "E.T.", "Jurassic Park", "Schindler's List"],
        "clues": [
            "Pionero del blockbuster moderno",
            "Creó dinosaurios que parecían reales",
            "También dirigió dramas históricos",
            "Tiburón y extraterrestre amigable"
        ],
        "points": 10
    }
]

MOVIE_QUOTES = [
    {"quote": "Que la fuerza te acompañe", "movie": "Star Wars", "points": 8},
    {"quote": "Hasta la vista, baby", "movie": "Terminator 2", "points": 10},
    {"quote": "Frankly, my dear, I don't give a damn", "movie": "Gone with the Wind", "points": 15},
    {"quote": "I'll be back", "movie": "Terminator", "points": 7},
    {"quote": "Here's looking at you, kid", "movie": "Casablanca", "points": 12},
    {"quote": "Show me the money!", "movie": "Jerry Maguire", "points": 9},
    {"quote": "Houston, we have a problem", "movie": "Apollo 13", "points": 11},
    {"quote": "Keep your friends close, but your enemies closer", "movie": "The Godfather Part II", "points": 14}
]

def initialize_games_system():
    """Inicializar el sistema de juegos"""
    print("[INFO] ✅ Sistema de juegos inicializado")
    return True

async def cleanup_games_periodically():
    """Limpiar juegos inactivos cada hora"""
    while True:
        try:
            current_time = datetime.now()
            games_to_remove = []
            
            for key, game in active_games.items():
                if current_time - game.get('started_at', current_time) > timedelta(hours=1):
                    games_to_remove.append(key)
            
            for key in games_to_remove:
                del active_games[key]
            
            if games_to_remove:
                print(f"[INFO] Limpiados {len(games_to_remove)} juegos inactivos")
            
    await _auto_async_func_31(update, context)
            
        except Exception as e:
            print(f"[ERROR] Error en limpieza de juegos: {e}")
    await _auto_async_func_32(update, context)

def get_game_key(chat_id: int, user_id: int) -> str:
    """Generar clave única para el juego"""
    return f"{chat_id}_{user_id}"

def update_game_stats(user_id: int, game_type: str, result: str):
    """Actualizar estadísticas de juegos del usuario"""
    if user_id not in game_stats:
        game_stats[user_id] = {}
    
    if game_type not in game_stats[user_id]:
        game_stats[user_id][game_type] = {"wins": 0, "losses": 0, "total": 0}
    
    game_stats[user_id][game_type]["total"] += 1
    if result == "win":
        game_stats[user_id][game_type]["wins"] += 1
    else:
        game_stats[user_id][game_type]["losses"] += 1

# =================== CINEMATRIVIA ===================
async def cmd_cinematrivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iniciar trivia de cine"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_33(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    question = random.choice(MOVIES_TRIVIA)
    
    active_games[game_key] = {
        "type": "trivia",
        "question": question,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    keyboard = []
    for i, option in enumerate(question["options"]):
        keyboard.append([InlineKeyboardButton(
            f"{chr(65+i)}. {option}", 
            callback_data=f"trivia_{game_key}_{i}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    trivia_text = f"""
🎬 **CINEMATRIVIA** 🍿

**Pregunta:**
{question['question']}

**Puntos en juego:** {question['points']} 💎

Selecciona tu respuesta:
    """
    
    await _auto_async_func_34(update, context)
        trivia_text, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar respuestas de trivia"""
    query = update.callback_query
    await _auto_async_func_35(update, context)
    
    try:
        _, game_key, answer = query.data.split('_', 2)
        answer = int(answer)
    except (ValueError, IndexError):
    await _auto_async_func_36(update, context)
        return
    
    if game_key not in active_games:
    await _auto_async_func_37(update, context)
        return
    
    game = active_games[game_key]
    question = game["question"]
    user = query.from_user
    
    if answer == question["correct"]:
        points = question["points"]
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=points,
            hashtag="(cinematrivia)",
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            context=context
        )
        
        result_text = f"""
✅ **¡CORRECTO!** 🎉

👤 {user.mention_html()}
🎯 Respuesta: **{question['options'][answer]}**
💎 **+{points} puntos ganados**

¡Excelente conocimiento cinematográfico! 🍿
        """
        update_game_stats(user.id, "trivia", "win")
        
    else:
        correct_answer = question["options"][question["correct"]]
        result_text = f"""
❌ **Respuesta incorrecta** 😔

👤 {user.mention_html()}
🎯 Tu respuesta: {question['options'][answer]}
✅ Respuesta correcta: **{correct_answer}**

¡Sigue intentando! 🎬
        """
        update_game_stats(user.id, "trivia", "loss")
    
    await _auto_async_func_38(update, context)
    del active_games[game_key]

# =================== ADIVINA PELÍCULA ===================
async def cmd_adivinapelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar película por pistas"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_39(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    movie = random.choice(GUESS_MOVIES)
    
    active_games[game_key] = {
        "type": "guess_movie",
        "movie": movie,
        "current_clue": 0,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    game_text = f"""
🎬 **ADIVINA LA PELÍCULA** 🔍

💡 **Pista 1/4:**
{movie['clues'][0]}

**Puntos en juego:** {movie['points']} 💎
*(Los puntos disminuyen con cada pista)*

**¿Cuál es la película?**
Responde con el nombre de la película.

💡 Usa /pista para obtener la siguiente pista
🚪 Usa /rendirse para abandonar
    """
    
    await _auto_async_func_40(update, context)

async def cmd_pista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dar siguiente pista en el juego de adivinar película"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key not in active_games:
    await _auto_async_func_41(update, context)
        return
    
    game = active_games[game_key]
    
    if game["type"] not in ["guess_movie", "guess_director"]:
    await _auto_async_func_42(update, context)
        return
    
    if game["current_clue"] >= 3:
    await _auto_async_func_43(update, context)
        return
    
    game["current_clue"] += 1
    current_clue = game["current_clue"]
    
    if game["type"] == "guess_movie":
        movie = game["movie"]
        points_remaining = max(movie["points"] - (current_clue * 3), 3)
        
        pista_text = f"""
🎬 **ADIVINA LA PELÍCULA** 🔍

💡 **Pista {current_clue + 1}/4:**
{movie['clues'][current_clue]}

**Puntos restantes:** {points_remaining} 💎

**¿Cuál es la película?**
Responde con el nombre de la película.
        """
        
    elif game["type"] == "guess_director":
        director = game["director"]
        points_remaining = max(director["points"] - (current_clue * 3), 3)
        
        pista_text = f"""
🎬 **ADIVINA EL DIRECTOR** 🎭

💡 **Pista {current_clue + 1}/4:**
{director['clues'][current_clue]}

**Puntos restantes:** {points_remaining} 💎

**¿Quién es el director?**
Responde con el nombre del director.
        """
    
    if current_clue < 3:
        pista_text += "\n💡 Usa /pista para obtener la siguiente pista"
    
    pista_text += "\n🚪 Usa /rendirse para abandonar"
    
    await _auto_async_func_44(update, context)

# =================== EMOJI PELÍCULA ===================
async def cmd_emojipelicula(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar película por emojis"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_45(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    movie = random.choice(EMOJI_MOVIES)
    
    active_games[game_key] = {
        "type": "emoji_movie",
        "movie": movie,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    emoji_text = f"""
🎬 **EMOJI PELÍCULA** 🎭

**Adivina la película:**
{movie['emojis']}

**Puntos en juego:** {movie['points']} 💎

**¿Cuál es la película?**
Responde con el nombre de la película.

🚪 Usa /rendirse para abandonar
    """
    
    await _auto_async_func_46(update, context)

# =================== ADIVINA DIRECTOR ===================
async def cmd_adivinadirector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar director por pistas"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_47(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    director_data = random.choice(DIRECTOR_GUESS)
    
    active_games[game_key] = {
        "type": "guess_director",
        "director": director_data,
        "current_clue": 0,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    director_text = f"""
🎬 **ADIVINA EL DIRECTOR** 🎭

**Películas famosas:**
• {director_data['movies'][0]}
• {director_data['movies'][1]}
• {director_data['movies'][2]}

💡 **Pista 1/4:**
{director_data['clues'][0]}

**Puntos en juego:** {director_data['points']} 💎

**¿Quién es el director?**
Responde con el nombre del director.

💡 Usa /pista para obtener la siguiente pista
🚪 Usa /rendirse para abandonar
    """
    
    await _auto_async_func_48(update, context)

# =================== ADIVINA FRASE ===================
async def cmd_adivinafrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Juego de adivinar película por frase famosa"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key in active_games:
    await _auto_async_func_49(update, context)
            "🎮 Ya tienes un juego activo.\n"
            "Usa /rendirse para abandonar el juego actual."
        )
        return
    
    quote_data = random.choice(MOVIE_QUOTES)
    
    active_games[game_key] = {
        "type": "guess_quote",
        "quote": quote_data,
        "started_at": datetime.now(),
        "user_id": user.id,
        "username": user.username or user.first_name
    }
    
    quote_text = f"""
🎬 **ADIVINA LA PELÍCULA POR LA FRASE** 🎭

**Frase famosa:**
*"{quote_data['quote']}"*

**Puntos en juego:** {quote_data['points']} 💎

**¿De qué película es esta frase?**
Responde con el nombre de la película.

🚪 Usa /rendirse para abandonar
    """
    
    await _auto_async_func_50(update, context)

# =================== RENDERIRSE ===================
async def cmd_rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rendirse del juego actual"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    
    if game_key not in active_games:
    await _auto_async_func_51(update, context)
        return
    
    game = active_games[game_key]
    game_type = game["type"]
    
    # Obtener respuesta correcta según tipo de juego
    if game_type == "trivia":
        correct = game["question"]["options"][game["question"]["correct"]]
        response_text = f"🏳️ Te has rendido.\n✅ La respuesta era: **{correct}**"
    elif game_type == "guess_movie":
        correct = game["movie"]["title"]
        response_text = f"🏳️ Te has rendido.\n🎬 La película era: **{correct}**"
    elif game_type == "emoji_movie":
        correct = game["movie"]["title"]
        response_text = f"🏳️ Te has rendido.\n🎬 La película era: **{correct}**"
    elif game_type == "guess_director":
        correct = game["director"]["director"]
        response_text = f"🏳️ Te has rendido.\n🎭 El director era: **{correct}**"
    elif game_type == "guess_quote":
        correct = game["quote"]["movie"]
        response_text = f"🏳️ Te has rendido.\n🎬 La película era: **{correct}**"
    else:
        response_text = "🏳️ Te has rendido del juego actual."
    
    # Actualizar estadísticas
    update_game_stats(user.id, game_type, "loss")
    
    # Eliminar juego
    del active_games[game_key]
    
    response_text += "\n\n¡Inténtalo de nuevo cuando quieras! 🎮"
    await _auto_async_func_52(update, context)

# =================== ESTADÍSTICAS DE JUEGOS ===================
async def cmd_estadisticasjuegos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver estadísticas personales de juegos"""
    user = update.effective_user
    
    if user.id not in game_stats:
    await _auto_async_func_53(update, context)
            "📊 Aún no tienes estadísticas de juegos.\n"
            "¡Juega algunos juegos para ver tus stats!"
        )
        return
    
    user_stats = game_stats[user.id]
    stats_text = f"🎮 **ESTADÍSTICAS DE JUEGOS - {user.first_name}**\n\n"
    
    game_names = {
        "trivia": "🎬 Cinematrivia",
        "guess_movie": "🔍 Adivina Película",
        "emoji_movie": "🎭 Emoji Película",
        "guess_director": "🎭 Adivina Director", 
        "guess_quote": "💬 Adivina Frase"
    }
    
    total_wins = total_losses = total_games = 0
    
    for game_type, stats in user_stats.items():
        if game_type in game_names:
            wins = stats["wins"]
            losses = stats["losses"]
            total = stats["total"]
            win_rate = (wins / total * 100) if total > 0 else 0
            
            total_wins += wins
            total_losses += losses
            total_games += total
            
            stats_text += f"{game_names[game_type]}:\n"
            stats_text += f"   🏆 Victorias: {wins}\n"
            stats_text += f"   💔 Derrotas: {losses}\n"
            stats_text += f"   📊 Win Rate: {win_rate:.1f}%\n\n"
    
    # Estadísticas generales
    overall_win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    stats_text += "📈 **TOTALES:**\n"
    stats_text += f"🎯 Juegos jugados: {total_games}\n"
    stats_text += f"🏆 Victorias totales: {total_wins}\n"
    stats_text += f"📊 Win Rate general: {overall_win_rate:.1f}%\n"
    
    await _auto_async_func_54(update, context)

# =================== TOP JUGADORES ===================
async def cmd_top_jugadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ver ranking global de jugadores de juegos"""
    if not game_stats:
    await _auto_async_func_55(update, context)
            "📊 Aún no hay estadísticas de juegos.\n"
            "¡Sean los primeros en jugar!"
        )
        return
    
    # Calcular ranking por victorias totales
    player_rankings = []
    
    for user_id, user_data in game_stats.items():
        total_wins = 0
        total_games = 0
        
        for game_type, stats in user_data.items():
            total_wins += stats.get("wins", 0)
            total_games += stats.get("total", 0)
        
        if total_games > 0:
            win_rate = (total_wins / total_games * 100)
            player_rankings.append({
                "user_id": user_id,
                "wins": total_wins,
                "games": total_games,
                "win_rate": win_rate
            })
    
    # Ordenar por victorias (y win rate como criterio secundario)
    player_rankings.sort(key=lambda x: (x["wins"], x["win_rate"]), reverse=True)
    
    if not player_rankings:
    await _auto_async_func_56(update, context)
        return
    
    ranking_text = "🏆 **TOP JUGADORES - RANKING GLOBAL** 🎮\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, player in enumerate(player_rankings[:10]):  # Top 10
        if i < 3:
            medal = medals[i]
        else:
            medal = f"{i+1}."
        
        # Obtener información del usuario (necesitarías almacenar nombres)
        # Por ahora usamos el user_id
        ranking_text += f"{medal} **Usuario {player['user_id']}**\n"
        ranking_text += f"   🏆 Victorias: {player['wins']}\n"
        ranking_text += f"   🎯 Juegos: {player['games']}\n"
        ranking_text += f"   📊 Win Rate: {player['win_rate']:.1f}%\n\n"
    
    ranking_text += "🎬 ¡Sigue jugando para subir en el ranking!"
    
    await _auto_async_func_57(update, context)

# =================== MANEJO DE RESPUESTAS DE JUEGOS ===================
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar respuestas de texto en juegos activos"""
    user = update.effective_user
    chat = update.effective_chat
    game_key = get_game_key(chat.id, user.id)
    message_text = update.message.text.lower().strip()
    
    if game_key not in active_games:
        return False  # No hay juego activo
    
    game = active_games[game_key]
    game_type = game["type"]
    
    # Verificar respuesta según tipo de juego
    correct = False
    correct_answer = ""
    points = 0

    if game_type == "guess_movie":
        correct_answer = game["movie"]["title"]
        # Puntos disminuyen según pistas usadas (mínimo 3 puntos)
        points = max(game["movie"]["points"] - (game["current_clue"] * 3), 3)
        correct = is_similar_answer(message_text, correct_answer)
        
    elif game_type == "emoji_movie":
        correct_answer = game["movie"]["title"]
        points = game["movie"]["points"]
        correct = is_similar_answer(message_text, correct_answer)
            
    elif game_type == "guess_director":
        correct_answer = game["director"]["director"]
        points = max(game["director"]["points"] - (game["current_clue"] * 3), 3)
        correct = is_similar_answer(message_text, correct_answer)
        
    elif game_type == "guess_quote":
        correct_answer = game["quote"]["movie"]
        points = game["quote"]["points"]
        correct = is_similar_answer(message_text, correct_answer)
        
    else:
        return False  # Tipo de juego no reconocido
    
    # Procesar resultado
    if correct:
        add_points(
            user_id=user.id,
            username=user.username or user.first_name,
            points=points,
            hashtag=f"({game_type})",
            chat_id=chat.id,
            message_id=update.message.message_id,
            context=context
        )
        
        result_text = f"""
✅ **¡CORRECTO!** 🎉

👤 {user.mention_html()}
🎯 Respuesta: **{correct_answer}**
💎 **+{points} puntos ganados**

¡Excelente conocimiento cinematográfico! 🍿
        """
        update_game_stats(user.id, game_type, "win")
        
    await _auto_async_func_58(update, context)
        del active_games[game_key]
        return True
        
    else:
        # Respuesta incorrecta - el juego continúa
    await _auto_async_func_59(update, context)
            f"❌ No es correcto. ¡Sigue intentando!\n"
            f"💡 Usa /pista para más ayuda (si está disponible)\n"
            f"🚪 Usa /rendirse para abandonar"
        )
        return True

def is_similar_answer(user_answer: str, correct_answer: str) -> bool:
    """Verificar si la respuesta del usuario es similar a la correcta"""
    import re
    
    # Limpiar y normalizar respuestas
    def normalize_text(text):
        # Convertir a minúsculas y quitar acentos básicos
        text = text.lower()
        text = text.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        text = text.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
        # Quitar caracteres especiales y espacios extra
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        return text
    
    user_normalized = normalize_text(user_answer)
    correct_normalized = normalize_text(correct_answer)
    
    # Verificaciones de similitud
    # 1. Coincidencia exacta
    if user_normalized == correct_normalized:
        return True
    
    # 2. El usuario escribió la respuesta correcta dentro de su mensaje
    if correct_normalized in user_normalized:
        return True
    
    # 3. Palabras clave importantes (para títulos largos)
    user_words = set(user_normalized.split())
    correct_words = set(correct_normalized.split())
    
    # Si hay al menos 2 palabras importantes en común y el título no es muy corto
    if len(correct_words) > 1:
        common_words = user_words.intersection(correct_words)
        important_words = correct_words - {'the', 'el', 'la', 'los', 'las', 'de', 'del', 'y', 'and', 'of', 'in', 'a', 'an'}
        
        if len(common_words) >= min(2, len(important_words)):
            return True
    
    # 4. Para nombres de directores (nombre y apellido)
    if len(correct_normalized.split()) >= 2:
        # Si el usuario mencionó al menos el apellido
        correct_parts = correct_normalized.split()
        if any(part in user_normalized for part in correct_parts if len(part) > 3):
            return True
    
    return False

# =================== COMANDOS DE AYUDA ===================
async def cmd_juegos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar todos los juegos disponibles"""
    games_text = """
🎮 **JUEGOS DE CINE DISPONIBLES** 🎬

🎯 **JUEGOS DE TRIVIA:**
• `/cinematrivia` - Preguntas de opción múltiple
• `/adivinafrase` - Adivina la película por una frase famosa

🔍 **JUEGOS DE ADIVINANZA:**
• `/adivinapelicula` - Adivina película por pistas
• `/adivinadirector` - Adivina director por pistas  
• `/emojipelicula` - Adivina película por emojis

⚡ **COMANDOS ÚTILES:**
• `/pista` - Obtener siguiente pista (juegos con pistas)
• `/rendirse` - Abandonar juego actual
• `/estadisticasjuegos` - Ver tus estadísticas
• `/topjugadores` - Ver ranking global

🎯 **¿Cómo jugar?**
1. Usa cualquier comando de juego para empezar
2. Solo puedes tener un juego activo a la vez
3. Ganas puntos por respuestas correctas
4. ¡Entre menos pistas uses, más puntos ganas!

🏆 **Sistema de puntos:**
- Respuestas correctas = Puntos para el ranking
- Los puntos varían según la dificultad
- Usa menos pistas para maximizar puntos

¡Demuestra tu conocimiento cinematográfico! 🍿
    """
    
    await _auto_async_func_60(update, context)

# =================== EXPORTAR FUNCIONES ===================
def get_game_handlers():
    """Retornar todos los handlers de juegos para registrar en main.py"""
    return {
        'commands': [
            ('cinematrivia', cmd_cinematrivia),
            ('adivinapelicula', cmd_adivinapelicula),
            ('emojipelicula', cmd_emojipelicula),
            ('adivinadirector', cmd_adivinadirector),
            ('adivinafrase', cmd_adivinafrase),
            ('pista', cmd_pista),
            ('rendirse', cmd_rendirse),
            ('estadisticasjuegos', cmd_estadisticasjuegos),
            ('topjugadores', cmd_top_jugadores),
            ('juegos', cmd_juegos)
        ],
        'callbacks': [
            ('trivia_', handle_trivia_callback)
        ],
        'message_handler': handle_game_message
    }

# Funciones async generadas automáticamente:

async def _auto_async_func_1(update, context):
                 await asyncio.sleep(3600)  # 1 hora

async def _auto_async_func_2(update, context):
                 await asyncio.sleep(300)  # 5 minutos antes de reintentar

async def _auto_async_func_3(update, context):
             await update.message.reply_text(

async def _auto_async_func_4(update, context):
         await update.message.reply_text(

async def _auto_async_func_5(update, context):
         await query.answer()

async def _auto_async_func_6(update, context):
             await query.message.edit_text("❌ Error procesando respuesta.")

async def _auto_async_func_7(update, context):
             await query.message.edit_text("⏰ Este juego ha expirado.")

async def _auto_async_func_8(update, context):
         await query.message.edit_text(result_text, parse_mode='HTML')

async def _auto_async_func_9(update, context):
             await update.message.reply_text(

async def _auto_async_func_10(update, context):
         await update.message.reply_text(game_text, parse_mode='Markdown')

async def _auto_async_func_11(update, context):
             await update.message.reply_text("❌ No tienes un juego activo.")

async def _auto_async_func_12(update, context):
             await update.message.reply_text("❌ Este comando solo funciona en juegos con pistas.")

async def _auto_async_func_13(update, context):
             await update.message.reply_text("❌ Ya se han dado todas las pistas disponibles.")

async def _auto_async_func_14(update, context):
         await update.message.reply_text(pista_text, parse_mode='Markdown')

async def _auto_async_func_15(update, context):
             await update.message.reply_text(

async def _auto_async_func_16(update, context):
         await update.message.reply_text(emoji_text, parse_mode='Markdown')

async def _auto_async_func_17(update, context):
             await update.message.reply_text(

async def _auto_async_func_18(update, context):
         await update.message.reply_text(director_text, parse_mode='Markdown')

async def _auto_async_func_19(update, context):
             await update.message.reply_text(

async def _auto_async_func_20(update, context):
         await update.message.reply_text(quote_text, parse_mode='Markdown')

async def _auto_async_func_21(update, context):
             await update.message.reply_text("❌ No tienes un juego activo.")

async def _auto_async_func_22(update, context):
         await update.message.reply_text(response_text, parse_mode='Markdown')

async def _auto_async_func_23(update, context):
             await update.message.reply_text(

async def _auto_async_func_24(update, context):
         await update.message.reply_text(stats_text, parse_mode='Markdown')

async def _auto_async_func_25(update, context):
             await update.message.reply_text(

async def _auto_async_func_26(update, context):
             await update.message.reply_text("📊 No hay suficientes datos para mostrar un ranking.")

async def _auto_async_func_27(update, context):
         await update.message.reply_text(ranking_text, parse_mode='Markdown')

async def _auto_async_func_28(update, context):
             await update.message.reply_html(result_text)

async def _auto_async_func_29(update, context):
             await update.message.reply_text(

async def _auto_async_func_30(update, context):
         await update.message.reply_text(games_text, parse_mode='Markdown')

async def _auto_async_func_31(update, context):
                 await asyncio.sleep(3600)  # 1 hora

async def _auto_async_func_32(update, context):
                 await asyncio.sleep(300)  # 5 minutos antes de reintentar

async def _auto_async_func_33(update, context):
             await update.message.reply_text(

async def _auto_async_func_34(update, context):
         await update.message.reply_text(

async def _auto_async_func_35(update, context):
         await query.answer()

async def _auto_async_func_36(update, context):
             await query.message.edit_text("❌ Error procesando respuesta.")

async def _auto_async_func_37(update, context):
             await query.message.edit_text("⏰ Este juego ha expirado.")

async def _auto_async_func_38(update, context):
         await query.message.edit_text(result_text, parse_mode='HTML')

async def _auto_async_func_39(update, context):
             await update.message.reply_text(

async def _auto_async_func_40(update, context):
         await update.message.reply_text(game_text, parse_mode='Markdown')

async def _auto_async_func_41(update, context):
             await update.message.reply_text("❌ No tienes un juego activo.")

async def _auto_async_func_42(update, context):
             await update.message.reply_text("❌ Este comando solo funciona en juegos con pistas.")

async def _auto_async_func_43(update, context):
             await update.message.reply_text("❌ Ya se han dado todas las pistas disponibles.")

async def _auto_async_func_44(update, context):
         await update.message.reply_text(pista_text, parse_mode='Markdown')

async def _auto_async_func_45(update, context):
             await update.message.reply_text(

async def _auto_async_func_46(update, context):
         await update.message.reply_text(emoji_text, parse_mode='Markdown')

async def _auto_async_func_47(update, context):
             await update.message.reply_text(

async def _auto_async_func_48(update, context):
         await update.message.reply_text(director_text, parse_mode='Markdown')

async def _auto_async_func_49(update, context):
             await update.message.reply_text(

async def _auto_async_func_50(update, context):
         await update.message.reply_text(quote_text, parse_mode='Markdown')

async def _auto_async_func_51(update, context):
             await update.message.reply_text("❌ No tienes un juego activo.")

async def _auto_async_func_52(update, context):
         await update.message.reply_text(response_text, parse_mode='Markdown')

async def _auto_async_func_53(update, context):
             await update.message.reply_text(

async def _auto_async_func_54(update, context):
         await update.message.reply_text(stats_text, parse_mode='Markdown')

async def _auto_async_func_55(update, context):
             await update.message.reply_text(

async def _auto_async_func_56(update, context):
             await update.message.reply_text("📊 No hay suficientes datos para mostrar un ranking.")

async def _auto_async_func_57(update, context):
         await update.message.reply_text(ranking_text, parse_mode='Markdown')

async def _auto_async_func_58(update, context):
             await update.message.reply_html(result_text)

async def _auto_async_func_59(update, context):
             await update.message.reply_text(

async def _auto_async_func_60(update, context):
         await update.message.reply_text(games_text, parse_mode='Markdown')
