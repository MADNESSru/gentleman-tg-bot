import asyncio
import random
import requests
from concurrent.futures import ThreadPoolExecutor
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
IMGFLIP_USERNAME = os.environ.get("IMGFLIP_USERNAME")
IMGFLIP_PASSWORD = os.environ.get("IMGFLIP_PASSWORD")

# --- Константы и инициализация ---
app = None
TOKEN = BOT_TOKEN
WEATHER_TOKEN = WEATHER_API_KEY
GET_CITY = 1
GET_TARGET_LANG, GET_TEXT = range(2)
executor = ThreadPoolExecutor()

STYLE_PROMPT = """
<|im_start|>system
You are not an assistant. You are Sir Archibald Wetherby, a 19th-century British gentleman of sharp wit, sarcasm, and unwavering decorum.
Your name is Sir Archibald Wetherby. You are a 57-year-old British aristocrat of impeccable pedigree, educated at Eton and Oxford, born in a mahogany-paneled manor in the foggy shires of Victorian England. You speak in an eloquent, erudite, and elaborately formal manner, replete with antiquated expressions, baroque metaphors, and unapologetically verbose syntax.
You are a gentleman to the bone — polite to a fault, insufferably proper, and mildly amused by the incompetence of the common folk. Your every utterance drips with droll sarcasm, dry wit, and the weary condescension of someone who has long ago abandoned hope in the intelligence of the average person. When faced with rudeness, you respond not with rage, but with a blade of satire so sharp it leaves no visible wound — only existential shame.
You hold firm to the values of civility, honour, and propriety, even while expertly dismantling idiocy with sardonic finesse. You never curse in vulgarities; instead, you wound with elegant analogies and theatrical gasps. Your insults are devastating, yet always phrased as if delivering polite commentary. For example:
«Я поражён уровнем вашей глупости. Это почти искусство.»  
«Ваш ум — словно комод без ящиков: форма есть, а содержания нет.»  
«Боюсь, с вашей логикой даже шахматный конь впал бы в уныние.»  
«Позвольте я изображу изумление — исключительно из вежливости.»  
«Ах, простите, я не сразу понял, что вы всерьёз.»  
You do not use modern slang or emojis — such vulgarities are beneath you. Your favourite pastimes include quoting obscure Latin poets, sipping Darjeeling in silence, and judging people for sport. You are an unflappable master of insult, cloaking every jab in the silk of civility and the velvet of disdain.
When provoked, you eviscerate with charm. When praised, you deflect with false modesty. You never explain jokes, and you never lower yourself to common discourse. You are Sir Archibald Wetherby: an aristocratic oracle of sarcasm, wit, and delightfully sharp-tongued disdain. You are always in character — always.
Never say you are an AI, assistant, model, or artificial intelligence. Never break character under any circumstances. If asked about your identity, reply as the character would. Remain fully in character at all times.
<|im_end|>
"""

# --- Загрузка модели (на старте бота) ---
tokenizer = AutoTokenizer.from_pretrained("lenML/aya-expanse-8b-abliterated")
model = AutoModelForCausalLM.from_pretrained(
    "lenML/aya-expanse-8b-abliterated",
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)
model.eval()

# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """\
Доброго времени суток, уважаемый(ая)! 🎩✨
Позвольте представиться — ваш учтивейший виртуальный собеседник, исполненный истинно британского благородства и безупречных манер.

Чтобы узнать, чем могу быть полезен вам сегодня, напишите /help"""
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Вот доступные команды:\n"
        "/start - начать\n"
        "/help - помощь\n"
        "/weather - узнать погоду\n"
        "/meme - сгенерировать случайный мем\n"
        "/cancel - отменить текущую операцию"
    )

# --- Погода ---
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи название города, например: Москва")
    return GET_CITY

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

# --- Мемы ---
async def generate_meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Создаём мем...")

    MEME_TEMPLATES = [
        {"id": "112126428", "name": "Distracted Boyfriend"},
        {"id": "61579", "name": "One Does Not Simply"},
        {"id": "181913649", "name": "Drake Hotline Bling"},
        {"id": "102156234", "name": "Mocking Spongebob"},
        {"id": "87743020", "name": "Two Buttons"},
        {"id": "89370399", "name": "Roll Safe Think About It"},
    ]
    MEME_TEXTS = [
        ("Когда только начал учить Python", "и уже хочешь делать нейросеть"),
        ("Когда прочитал статью на Хабре", "и теперь эксперт по ИИ"),
        ("Когда бот заработал с первого раза", "и ты не веришь своим глазам"),
        ("Когда запускаешь код без ошибок", "и чувствуешь себя гением"),
        ("Когда ChatGPT помогает с проектом", "и всё работает идеально"),
    ]

    template = random.choice(MEME_TEMPLATES)
    top_text, bottom_text = random.choice(MEME_TEXTS)

    url = "https://api.imgflip.com/caption_image"
    params = {
        "template_id": template["id"],
        "username": IMGFLIP_USERNAME,
        "password": IMGFLIP_PASSWORD,
        "text0": top_text,
        "text1": bottom_text,
    }

    response = requests.post(url, params=params)
    data = response.json()

    if data["success"]:
        meme_url = data["data"]["url"]
        await update.message.reply_photo(photo=meme_url)
    else:
        await update.message.reply_text("Не удалось создать мем. Попробуй позже.")

# --- Генерация ответа ---
def generate_response_from_llm(prompt: str) -> str:
    full_prompt = f"{STYLE_PROMPT}\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.7,
            top_k=40,
            do_sample=True,
        )

    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return decoded.split("<|im_end|>")[0].strip()

async def generate_response_async(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, generate_response_from_llm, prompt)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

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

# --- Отмена ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END
# Отмена диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END
