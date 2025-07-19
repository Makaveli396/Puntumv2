from telegram import Update
from db import add_points
from handlers.retos import get_weekly_challenge, validate_challenge_submission, get_current_challenge
from handlers.retos_diarios import get_today_challenge
from handlers.phrases import get_random_reaction
import re

POINTS = {
    "#aporte": 3,
    "#recomendación": 5,
    "#reseña": 7,
    "#crítica": 10,
    "#debate": 4,
    "#pregunta": 2,
    "#spoiler": 1,
}

user_hashtag_cache = {}

def count_words(text):
    """Cuenta palabras sin incluir hashtags"""
    text_without_hashtags = re.sub(r'#\w+', '', text)
    return len(text_without_hashtags.split())

def is_spam(user_id, hashtag):
    """Detecta spam basado en frecuencia de hashtags por usuario"""
    import time
    current_time = time.time()

    if user_id not in user_hashtag_cache:
        user_hashtag_cache[user_id] = {}

    user_data = user_hashtag_cache[user_id]

    if hashtag in user_data:
        if current_time - user_data.get("last_time", 0) < 300:  # 5 minutos
            user_data[hashtag] = user_data.get(hashtag, 0) + 1
            if user_data[hashtag] > 3:  # Máximo 3 hashtags iguales en 5 min
                return True
        else:
            user_data[hashtag] = 1
    else:
        user_data[hashtag] = 1

    user_data["last_time"] = current_time
    return False

async def handle_hashtags(update: Update, context):
    """Handler principal para procesar hashtags y otorgar puntos"""
    text = update.message.text if update.message and update.message.text else ""
    user = update.effective_user
    points = 0
    found_tags = []
    warnings = []
    response = ""

    print(f"[DEBUG] handle_hashtags procesando: {text[:50]}...")

    # Procesar hashtags básicos
    for tag, value in POINTS.items():
        if tag in text.lower():
            # Verificar spam
            if is_spam(user.id, tag):
                warnings.append(f"⚠️ {tag}: Detectado spam. Usa hashtags con moderación.")
                continue

            # Validaciones especiales por hashtag
            if tag == "#reseña":
                word_count = count_words(text)
                if word_count < 50:
                    warnings.append(f"❌ {tag}: Necesitas mínimo 50 palabras. Tienes {word_count}.")
                    continue

            elif tag == "#crítica":
                word_count = count_words(text)
                if word_count < 100:
                    warnings.append(f"❌ {tag}: Necesitas mínimo 100 palabras. Tienes {word_count}.")
                    continue

            elif tag == "#recomendación":
                # Buscar formato "Título, País, Año"
                has_pattern = bool(re.search(r'[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*\d{4}', text))
                if not has_pattern:
                    warnings.append(f"💡 {tag}: Incluye formato 'Título, País, Año' para máximos puntos.")
                    value = 3  # Reducir puntos si no tiene formato completo

            points += value
            found_tags.append(f"{tag} (+{value})")

    # Procesar solo si hay puntos o advertencias
    if points > 0 or warnings:
        # Agregar puntos básicos a la base de datos
        try:
            result = add_points(
                user.id,
                user.username,
                points,
                hashtag=None,
                message_text=text,
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                is_challenge_bonus=False,
                context=context
            )
        except Exception as e:
            print(f"[ERROR] Error agregando puntos básicos: {e}")

        # Construir respuesta para puntos básicos
        if points > 0:
            tags_text = ", ".join(found_tags)
            tag_main = found_tags[0].split()[0] if found_tags else "default"
            try:
                reaction = get_random_reaction(tag_main, user.id)
                response += f"✅ +{points} puntos por: {tags_text}\n{reaction}\n"
            except Exception as e:
                print(f"[ERROR] Error obteniendo reacción: {e}")
                response += f"✅ +{points} puntos por: {tags_text}\n"

        # Agregar advertencias
        if warnings:
            response += "\n".join(warnings) + "\n"

        # Verificar reto semanal
        try:
            current_challenge = get_current_challenge()
            if current_challenge and current_challenge.get("hashtag"):
                hashtag_challenge = current_challenge["hashtag"]
                if hashtag_challenge in text.lower():
                    if validate_challenge_submission(current_challenge, text):
                        bonus = current_challenge.get("bonus_points", 10)
                        try:
                            bonus_result = add_points(
                                user.id,
                                user.username,
                                bonus,
                                hashtag=hashtag_challenge,
                                message_text=text,
                                chat_id=update.effective_chat.id,
                                message_id=update.message.message_id,
                                is_challenge_bonus=True,
                                context=context
                            )
                            response += f"\n🎯 ¡Reto semanal completado! Bonus: +{bonus} puntos 🎉"
                        except Exception as e:
                            print(f"[ERROR] Error agregando bonus semanal: {e}")
        except Exception as e:
            print(f"[ERROR] Error validando reto semanal: {e}")

        # Verificar reto diario
        try:
            daily = get_today_challenge()
            if daily:
                cumple = False

                # Verificar hashtag específico
                if "hashtag" in daily and daily["hashtag"] in text.lower():
                    cumple = True
                # Verificar palabras clave
                elif "keywords" in daily:
                    cumple = any(word in text.lower() for word in daily["keywords"])

                # Verificar longitud mínima si se requiere
                if cumple and "min_words" in daily:
                    word_count = count_words(text)
                    if word_count < daily["min_words"]:
                        cumple = False

                if cumple:
                    daily_bonus = daily.get("bonus_points", 5)
                    try:
                        bonus_result = add_points(
                            user.id,
                            user.username,
                            daily_bonus,
                            hashtag="(reto_diario)",
                            message_text=text,
                            chat_id=update.effective_chat.id,
                            message_id=update.message.message_id,
                            is_challenge_bonus=True,
                            context=context
                        )
                        response += f"\n🎯 ¡Reto diario completado! Bonus: +{daily_bonus} puntos 🎉"
                    except Exception as e:
                        print(f"[ERROR] Error agregando bonus diario: {e}")
        except Exception as e:
            print(f"[ERROR] Error validando reto diario: {e}")

        # Enviar respuesta si hay contenido
        if response.strip():
            try:
                await update.message.reply_text(response.strip())
            except Exception as e:
                print(f"[ERROR] Error enviando respuesta: {e}")

    # Detección de spam adicional
    spam_words = ["gratis", "oferta", "descuento", "promoción", "gana dinero", "click aquí"]
    if any(spam_word in text.lower() for spam_word in spam_words):
        try:
            await update.message.reply_text("🛑 ¡Cuidado con el spam! Esto es un grupo de cine, no de ofertas.")
        except Exception as e:
            print(f"[ERROR] Error enviando advertencia de spam: {e}")
