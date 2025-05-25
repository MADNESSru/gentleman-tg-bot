app = None
TOKEN = BOT_TOKEN
WEATHER_TOKEN = WEATHER_API_KEY
GET_CITY = 1
GET_TARGET_LANG, GET_TEXT = range(2)

executor = ThreadPoolExecutor()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
        Доброго времени суток, уважаемый(ая)! 🎩✨
Позвольте представиться — ваш учтивейший виртуальный собеседник, исполненный истинно британского благородства и безупречных манер. К вашим услугам — изысканные беседы, тонкий юмор и, разумеется, безукоризненная вежливость \n
Чтобы узнать, чем могу быть полезен вам сегодня, напишите /help
        """
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Вот доступные команды:\n"
        "/start - начать\n"
        "/help - помощь\n"
        "/weather - узнать погоду\n"
        "/meme - сгенерировать случайный мем\n"
        "/cancel - отменить текущую операцию"
    )

# /weather — начало
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи название города, например: Москва")
    return GET_CITY

# Получаем город и отправляем погоду
async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_TOKEN}&units=metric&lang=ru"
    response = requests.get(url).json()

    if response.get("cod") != 200:
        await update.message.reply_text("Город не найден. Попробуй снова.")
        return GET_CITY

    temp = response["main"]["temp"]
    desc = response["weather"][0]["description"]
    await update.message.reply_text(f"Погода в {city}:\n{temp}°C, {desc}")
    return ConversationHandler.END

async def generate_meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Создаём мем...")

    MEME_TEMPLATES = [
    {"id": "112126428", "name": "Distracted Boyfriend"},
    {"id": "61579", "name": "One Does Not Simply"},
    {"id": "181913649", "name": "Drake Hotline Bling"},
    {"id": "102156234", "name": "Mocking Spongebob"},
    {"id": "87743020", "name": "Two Buttons"},
    {"id": "89370399", "name": "Roll Safe Think About It"},]

    MEME_TEXTS = [
    ("Когда только начал учить Python", "и уже хочешь делать нейросеть"),
    ("Когда прочитал статью на Хабре", "и теперь эксперт по ИИ"),
    ("Когда бот заработал с первого раза", "и ты не веришь своим глазам"),
    ("Когда запускаешь код без ошибок", "и чувствуешь себя гением"),
    ("Когда ChatGPT помогает с проектом", "и всё работает идеально"),]

    template = random.choice(MEME_TEMPLATES)
    top_text, bottom_text = random.choice(MEME_TEXTS)

    url = "https://api.imgflip.com/caption_image"
    params = {
        "template_id": template["id"],
        "username": IMGFLIP_USERNAME,
        "password": IMGFLIP_PASSWORD,
        "text0": top_text,
        "text1": bottom_text
    }

    response = requests.post(url, params=params)
    data = response.json()

    if data["success"]:
        meme_url = data["data"]["url"]
        await update.message.reply_photo(photo=meme_url)
    else:
        await update.message.reply_text("Не удалось создать мем. Попробуй позже.")


# Генерация ответа от LLM
def generate_response_from_llm(prompt: str) -> str:
    full_prompt = f"{STYLE_PROMPT}\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "temperature": 0.7,
            "top_k": 40,
            "max_new_tokens": 100,
            "return_full_text": False
        },
        "options": {
            "wait_for_model": True  # важно, иначе может возвращаться 503
        }
    }

    response = requests.post(HF_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        return result[0]["generated_text"].strip().split("<|im_end|>")[0]
    else:
        print("Ошибка Hugging Face API:", response.status_code, response.text)
        return "Прошу прощения уважаемый(ая), но я не смог получить ответ от сервера Hugging Face."


# Обработчик текстовых сообщений
async def generate_response_async(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, generate_response_from_llm, prompt)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    # Фоновая задача: шлёт "typing", пока не закончим генерацию
    async def send_typing():
        while not typing_task.done():
            await update.message.chat.send_action("typing")
            await asyncio.sleep(1.5)

    typing_task = asyncio.create_task(generate_response_async(user_input))
    typing_indicator = asyncio.create_task(send_typing())

    try:
        reply = await typing_task
        await update.message.reply_text(reply)
    except Exception as e:
        print("Ошибка в handle_text:", e)
        await update.message.reply_text(
            "Прошу прощения, но я столкнулся с проблемой. Видимо, чёрнила в моём виртуальном пере закончились."
        )
    finally:
        typing_indicator.cancel()

# Отмена диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END
