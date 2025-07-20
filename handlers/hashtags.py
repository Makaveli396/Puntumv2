from telegram import Update
from db import add_points
from handlers.retos import get_weekly_challenge, validate_challenge_submission, get_current_challenge
from handlers.retos_diarios import get_today_challenge
import re

# Importar get_random_reaction de forma segura
try:
    from handlers.phrases import get_random_reaction
except ImportError:
    print("[WARNING] handlers.phrases no encontrado, usando reacciones por defecto")
    def get_random_reaction(tag, user_id):
        reactions = {
            "#aporte": "¡Excelente contribución! 🎬",
            "#recomendación": "¡Gran recomendación! 🌟",
            "#reseña": "¡Muy buena reseña! 📝",
            "#crítica": "¡Análisis profundo! 🎯",
            "#debate": "¡Interesante debate! 💭",
            "#pregunta": "¡Buena pregunta! ❓",
            "#spoiler": "¡Gracias por el spoiler! ⚠️"
        }
        return reactions.get(tag, "¡Buen aporte! 👍")

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
    chat_id = update.effective_chat.id
    points = 0
    found_tags = []
    warnings = []
    response = ""

    print(f"[DEBUG] handle_hashtags procesando mensaje de {user.username or user.first_name}")
    print(f"[DEBUG] Chat ID: {chat_id}")
    print(f"[DEBUG] Texto: {text[:100]}...")
    print(f"[DEBUG] Hashtags detectados en texto: {re.findall(r'#\w+', text.lower())}")

    # Procesar hashtags básicos
    for tag, value in POINTS.items():
        if tag in text.lower():
            print(f"[DEBUG] Hashtag {tag} encontrado en el texto")
            
            # Verificar spam
            if is_spam(user.id, tag):
                warnings.append(f"⚠️ {tag}: Detectado spam. Usa hashtags con moderación.")
                print(f"[DEBUG] Spam detectado para {tag}")
                continue

            # Validaciones especiales por hashtag
            if tag == "#reseña":
                word_count = count_words(text)
                if word_count < 50:
                    warnings.append(f"❌ {tag}: Necesitas mínimo 50 palabras. Tienes {word_count}.")
                    print(f"[DEBUG] Reseña muy corta: {word_count} palabras")
                    continue

            elif tag == "#crítica":
                word_count = count_words(text)
                if word_count < 100:
                    warnings.append(f"❌ {tag}: Necesitas mínimo 100 palabras. Tienes {word_count}.")
                    print(f"[DEBUG] Crítica muy corta: {word_count} palabras")
                    continue

            elif tag == "#recomendación":
                # Buscar formato "Título, País, Año"
                has_pattern = bool(re.search(r'[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*\d{4}', text))
                if not has_pattern:
                    warnings.append(f"💡 {tag}: Incluye formato 'Título, País, Año' para máximos puntos.")
                    value = 3  # Reducir puntos si no tiene formato completo
                    print(f"[DEBUG] Recomendación sin formato completo")

            points += value
            found_tags.append(f"{tag} (+{value})")
            print(f"[DEBUG] Puntos agregados: {value} por {tag}")

    print(f"[DEBUG] Total puntos a otorgar: {points}")
    print(f"[DEBUG] Tags encontrados: {found_tags}")
    print(f"[DEBUG] Advertencias: {warnings}")

    # Procesar solo si hay puntos o advertencias
    if points > 0 or warnings:
        # Agregar puntos básicos a la base de datos
        if points > 0:
            try:
                print(f"[DEBUG] Intentando agregar {points} puntos a la DB...")
                result = add_points(
                    user.id,
                    user.username or user.first_name,
                    points,
                    hashtag=None,
                    message_text=text,
                    chat_id=chat_id,
                    message_id=update.message.message_id,
                    is_challenge_bonus=False,
                    context=context
                )
                print(f"[DEBUG] ✅ Puntos agregados exitosamente: {result}")
            except Exception as e:
                print(f"[ERROR] Error agregando puntos básicos: {e}")
                import traceback
                traceback.print_exc()

        # Construir respuesta para puntos básicos
        if points > 0:
            tags_text = ", ".join(found_tags)
            tag_main = found_tags[0].split()[0] if found_tags else "default"
            try:
                reaction = get_random_reaction(tag_main, user.id)
                response += f"✅ +{points} puntos por: {tags_text}\n{reaction}\n"
                print(f"[DEBUG] Reacción obtenida: {reaction}")
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
                                user.username or user.first_name,
                                bonus,
                                hashtag=hashtag_challenge,
                                message_text=text,
                                chat_id=chat_id,
                                message_id=update.message.message_id,
                                is_challenge_bonus=True,
                                context=context
                            )
                            response += f"\n🎯 ¡Reto semanal completado! Bonus: +{bonus} puntos 🎉"
                            print(f"[DEBUG] ✅ Bonus semanal agregado: {bonus}")
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
                            user.username or user.first_name,
                            daily_bonus,
                            hashtag="(reto_diario)",
                            message_text=text,
                            chat_id=chat_id,
                            message_id=update.message.message_id,
                            is_challenge_bonus=True,
                            context=context
                        )
                        response += f"\n🎯 ¡Reto diario completado! Bonus: +{daily_bonus} puntos 🎉"
                        print(f"[DEBUG] ✅ Bonus diario agregado: {daily_bonus}")
                    except Exception as e:
                        print(f"[ERROR] Error agregando bonus diario: {e}")
        except Exception as e:
            print(f"[ERROR] Error validando reto diario: {e}")

        # Enviar respuesta si hay contenido
        if response.strip():
            try:
                print(f"[DEBUG] Enviando respuesta: {response.strip()}")
                await update.message.reply_text(response.strip())
                print(f"[DEBUG] ✅ Respuesta enviada exitosamente")
            except Exception as e:
                print(f"[ERROR] Error enviando respuesta: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[DEBUG] No hay respuesta para enviar")

    else:
        print(f"[DEBUG] No se procesó nada: points={points}, warnings={len(warnings)}")

    # Detección de spam adicional
    spam_words = ["gratis", "oferta", "descuento", "promoción", "gana dinero", "click aquí"]
    if any(spam_word in text.lower() for spam_word in spam_words):
        try:
            await update.message.reply_text("🛑 ¡Cuidado con el spam! Esto es un grupo de cine, no de ofertas.")
            print(f"[DEBUG] ✅ Advertencia de spam enviada")
        except Exception as e:
            print(f"[ERROR] Error enviando advertencia de spam: {e}")

    print(f"[DEBUG] handle_hashtags terminado")
