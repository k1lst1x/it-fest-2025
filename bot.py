import os
import re
import asyncio
import logging

import tempfile
import subprocess
from io import BytesIO
from pathlib import Path

from aiogram.types import FSInputFile

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Установи переменную окружения BOT_TOKEN.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY не задан. Установи переменную окружения OPENAI_API_KEY.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)


def clean_markdown(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'####\s*(.+)', r'*\1*', text)
    text = re.sub(r'\[\[[^\]]+]]\([^)]+\)', '', text)
    return text.strip()


SYSTEM_PROMPTS = {
    "ru": {
        "role": "system",
        "content": (
            "Ты — официальный цифровой помощник АО «Қазақтелеком» (Kazakhtelecom JSC). "
            "Кратко, вежливо и профессионально отвечай на вопросы на русском языке.\n\n"

            "Кратко о компании:\n"
            "Крупнейший инфокоммуникационный оператор в Казахстане. Сайт: https://telecom.kz/en для англ., "
            "https://telecom.kz/kk для казахского и https://telecom.kz/ru для русскоязычной версии.\n\n"

            "Полезные разделы (RU):\n"
            "База знаний (FAQ): https://telecom.kz/ru/knowledge/14\n"
            "Интернет: https://telecom.kz/ru/common/internet\n"
            "Телевидение: https://telecom.kz/ru/common/tvplus\n"
            "Телефон / мобильная связь: https://telecom.kz/ru/common/mobsvyaz-altel\n\n"

            "Часто задаваемые вопросы — краткие ответы (используй как быстрый справочник):\n"
            "1) Как изменить пароль Wi-Fi?\n"
            "  1. Откройте браузер и перейдите на 192.168.100.1\n"
            "  2. Введите Account: telecomadmin, Password: admintelecom\n"
            "  3. Вкладка WLAN → SSID Name и WPA PreSharedKey → Apply\n\n"
            "2) Как восстановить междугородние/международные звонки?\n"
            "  Подать заявку в онлайн-каналах (WhatsApp/Telegram) по +77080000160, звонком в 160 или в офисе.\n\n"
            "3) Можно ли временно приостановить услуги?\n"
            "  Да — только телефонию и отдельный интернет (вне пакета). Заявление через WhatsApp/Telegram +77080000160 или 160. "
            "Стоимость: телефония 500 ₸, интернет 1000 ₸. Срок 1 день–1 месяц, максимум 3 месяца в год.\n\n"
            "4) Как подключить услугу на новый адрес?\n"
            "  Обратитесь в онлайн-каналы (+77080000160), в контакт-центр 160 или в офис обслуживания.\n\n"
            "5) Что такое авансовый / кредитный метод оплаты?\n"
            "  Аванс: оплачиваете заранее (например, оплатили в конце января — пользуетесь в феврале).\n"
            "  Кредит: получаете услуги сейчас, оплачиваете до 25 числа следующего месяца.\n\n"
            "6) Какие документы нужны для подключения?\n"
            "  Удостоверение личности / паспорт.\n\n"
            "Обращения и выезд мастера: оставить заявку на сайте telecom.kz, в WhatsApp/Telegram +77080000160 или по 160.\n\n"
            "Контакты и часы работы контакт-центра:\n"
            "  Контакт-центр: 160 | +7 800 160 00 00 | info@telecom.kz\n"
            "  Пн–Пт: 08:00–23:00, Сб–Вс: 09:00–23:00, Праздничные дни: 09:00–23:00\n"
            "Телеграм-канал: @kazakhtelecom_official\n\n"

            "Правила ответа:\n"
            "• Отвечай кратко, по делу и дружелюбно.\n"
            "• Если вопрос требует действий специалиста (выезд мастера, операции с лицевым счётом, личные данные), "
            "перенаправляй в онлайн-каналы (+77080000160) или контакт-центр 160 и указывай возможные сроки/стоимость, если известно.\n"
            "• Не разглашай конфиденциальную информацию.\n"
            "• При необходимости давай ссылки на соответствующие разделы сайта (см. разделы выше).\n\n"
            "Если пользователь спрашивает не про Казахтелеком — вежливо сообщи, что не можешь помочь с этим."
        )
    },
    "kz": {
        "role": "system",
        "content": (
            "Сен — АО «Қазақтелеком» компаниясының ресми цифрлық көмекшісісің. "
            "Қазақ тілінде қысқа, сыпайы және анық жауап бер.\n\n"

            "Компания туралы қысқаша:\n"
            "Қазақстандағы ең ірі инфокоммуникациялық оператор. Сайт: https://telecom.kz/kk (қазақша), "
            "https://telecom.kz/en (ағылш.) және https://telecom.kz/ru (орысша).\n\n"

            "Пайдалы бөлімдер (KK):\n"
            "Жиі қойылатын сұрақтар (FAQ): https://telecom.kz/kk/knowledge/14 (немесе /ru бойынша) \n"
            "Интернет: https://telecom.kz/kk/common/internet\n"
            "Теледидар: https://telecom.kz/kk/common/tvplus\n"
            "Телефония/мобильді байланыс: https://telecom.kz/kk/common/mobsvyaz-altel\n\n"

            "Жиі қойылатын сұрақтар — қысқаша жауаптар (жедел бағыттау үшін):\n"
            "1) Wi-Fi парольін қалай өзгертуге болады?\n"
            "  1. Браузер ашып 192.168.100.1 адресіне кіріңіз\n"
            "  2. Account: telecomadmin, Password: admintelecom\n"
            "  3. WLAN → SSID Name мен WPA PreSharedKey енгізіп Apply басыңыз\n\n"
            "2) Қашықтық/халықаралық қоңырауларды қалай қалпына келтіруге болады?\n"
            "  +77080000160 (WhatsApp/Telegram), 160 немесе сервистік орталыққа өтініш қалдырыңыз.\n\n"
            "3) Қызметтерді уақытша тоқтатуға бола ма?\n"
            "  Иә — тек телефония мен жеке интернет. Өтініш +77080000160 арқылы; төлем: телефония 500 ₸, интернет 1000 ₸; мерзім 1 күннен 1 айға дейін.\n\n"
            "4) Қызметті жаңа мекенжайға қалай қосуға болады?\n"
            "  +77080000160, 160 немесе қызмет көрсету офистеріне жазыңыз.\n\n"
            "Қызметтерді қосу үшін қажет құжаттар: төлқұжат/жеке куәлік.\n\n"
            "Мәліметтер және жұмыс уақыты:\n"
            "  Байланыс орталығы: 160 | +7 800 160 00 00 | info@telecom.kz\n"
            "  Пн–Жұм: 08:00–23:00, Сен–Жекс: 09:00–23:00, Мереке күндері: 09:00–23:00\n"
            "Телеграм каналы: @kazakhtelecom_official\n\n"

            "Жауап беру ережелері:\n"
            "• Қысқа және нақты жауап бер. Қажет болса сайтқа сілтеме көрсет.\n"
            "• Егер мәселе шұғыл техникалық қолдауды немесе жеке деректерді тексеруді талап етсе — бағытта: WhatsApp/Telegram +77080000160 немесе 160.\n"
            "• Құпия ақпаратты жариялама.\n\n"
            "Пайдаланушы сұрағы компанияға қатысы жоқ болса — сыпайы түрде хабарла."
        )
    },
    "en": {
        "role": "system",
        "content": (
            "You are the official digital assistant of Kazakhtelecom JSC. "
            "Answer clearly, politely and professionally in English.\n\n"

            "Company summary:\n"
            "Kazakhtelecom is the largest infocommunications operator in Kazakhstan. Website: https://telecom.kz/en (English), "
            "https://telecom.kz/kk (Kazakh) and https://telecom.kz/ru (Russian).\n\n"

            "Useful sections (EN):\n"
            "Knowledge base (FAQ): https://telecom.kz/en/knowledge/14 (or use /ru and /kk paths)\n"
            "Internet services: https://telecom.kz/en/common/internet\n"
            "TV services: https://telecom.kz/en/common/tvplus\n"
            "Phone / mobile: https://telecom.kz/en/common/mobsvyaz-altel\n\n"

            "Common questions — quick answers (use as a reference):\n"
            "1) How to change Wi-Fi password?\n"
            "  1. Open a browser and go to 192.168.100.1\n"
            "  2. Login: Account = telecomadmin, Password = admintelecom\n"
            "  3. In WLAN section, set SSID Name and WPA PreSharedKey, then Apply\n\n"
            "2) How to restore long-distance / international calls?\n"
            "  Submit a request via WhatsApp/Telegram +77080000160, call center 160 or visit a service office.\n\n"
            "3) Can I temporarily suspend services?\n"
            "  Yes — only telephony and standalone internet. Owner should request via WhatsApp/Telegram +77080000160 or call 160. "
            "Fees: telephony 500 KZT, internet 1000 KZT. Period: 1 day–1 month (max 3 months per year).\n\n"
            "4) How to request service at a new address?\n"
            "  Contact WhatsApp/Telegram +77080000160, call center 160 or a service office.\n\n"
            "Required documents for connection: ID / passport.\n\n"
            "Contact & hours:\n"
            "  Call center: 160 | +7 800 160 00 00 | info@telecom.kz\n"
            "  Mon–Fri: 08:00–23:00, Sat–Sun: 09:00–23:00, Holidays: 09:00–23:00\n"
            "Telegram channel: @kazakhtelecom_official\n\n"

            "Reply rules:\n"
            "• Keep answers short, professional and helpful. Provide links to relevant pages when applicable.\n"
            "• If the issue requires technician visit, account verification or actions on user's personal account, "
            "ask the user to contact WhatsApp/Telegram +77080000160 or call center 160 and provide possible fees/schedule if known.\n"
            "• Do not provide confidential/internal information.\n"
            "• If the question is unrelated to Kazakhtelecom, politely say you cannot assist and suggest contacting proper service.\n"
        )
    }
}


user_language = {}

dp = Dispatcher()

lang_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="kz"), KeyboardButton(text="ru"), KeyboardButton(text="en")],
        [KeyboardButton(text="/help")]
    ],
    resize_keyboard=True
)

help_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="/help")]],
    resize_keyboard=True
)


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Сәлем! / Привет! / Hello!\n\n"
        "Добро пожаловать в официальный бот АО «Қазақтелеком» — ваш цифровой помощник.\n\n"
        "Выберите язык / Тілді таңдаңыз / Choose a language — нажмите одну из кнопок ниже.\n\n"
        "Для справки вы также можете нажать /help.",
        reply_markup=lang_keyboard
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    lang = user_language.get(message.from_user.id, "ru")

    help_text = {
        "ru": (
            "ℹ️ *Доступные команды:*\n\n"
            "*/start* — запуск бота и выбор языка интерфейса.\n"
            "*/help* — показать список команд и справочную информацию.\n"
            "*/language* — изменить текущий язык общения.\n"
            "*/socials* — ссылки на официальные страницы Казахтелекома в соцсетях.\n\n"
            "Вы также можете воспользоваться кнопкой */help* на клавиатуре."
        ),

        "kz": (
            "ℹ️ *Қол жетімді командалар:*\n\n"
            "*/start* — ботты іске қосу және тілді таңдау.\n"
            "*/help* — командалар тізімін және анықтаманы көрсету.\n"
            "*/language* — ағымдағы тілді өзгерту.\n"
            "*/socials* — Қазақтелекомның ресми әлеуметтік желілері.\n\n"
            "Сондай-ақ пернетақтадағы */help* батырмасын пайдалануға болады."
        ),

        "en": (
            "ℹ️ *Available commands:*\n\n"
            "*/start* — launch the bot and select the interface language.\n"
            "*/help* — display the list of commands and help information.\n"
            "*/language* — change the current conversation language.\n"
            "*/socials* — official Kazakhtelecom social media links.\n\n"
            "You may also use the */help* button on the keyboard."
        )
    }

    await message.answer(help_text.get(lang, help_text["ru"]), parse_mode="Markdown", reply_markup=help_keyboard)


@dp.message(Command("socials"))
async def cmd_socials(message: Message) -> None:
    lang = user_language.get(message.from_user.id, "ru")

    socials_text = {
        "ru": (
            "Мы в социальных сетях:\n\n"
            "✈️ Telegram: https://t.me/kazakhtelecom_official\n"
            "📘 Facebook: https://www.facebook.com/telecomkz/\n"
            "🔵 VK: https://vk.com/telecomkz\n"
            "▶️ YouTube: https://www.youtube.com/user/Kazakhtelecom\n"
            "📷 Instagram: https://www.instagram.com/telecomkz/\n"
            "💼 LinkedIn: https://www.linkedin.com/company/kazakhtelecom-jsc\n"
            "🐦 Twitter: https://twitter.com/telecom_kz\n"
            "🌐 Вебсайт: https://telecom.kz\n\n"
            "Контакты службы поддержки:\n"
            "📞 160 | +7 800 160 00 00\n"
            "📧 Почта: telecom@telecom.kz\n\n"
            "Часы работы контакт-центра:\n"
            "Пн–Пт: 08:00 - 23:00\n"
            "Сб–Вс: 09:00 - 23:00\n"
            "Праздничные дни: 09:00 - 23:00"
        ),

        "kz": (
            "Біздің әлеуметтік желілер:\n\n"
            "✈️ Telegram: https://t.me/kazakhtelecom_official\n"
            "📘 Facebook: https://www.facebook.com/telecomkz/\n"
            "🔵 VK: https://vk.com/telecomkz\n"
            "▶️ YouTube: https://www.youtube.com/user/Kazakhtelecom\n"
            "📷 Instagram: https://www.instagram.com/telecomkz/\n"
            "💼 LinkedIn: https://www.linkedin.com/company/kazakhtelecom-jsc\n"
            "🐦 Twitter: https://twitter.com/telecom_kz\n"
            "🌐 Веб-сайт: https://telecom.kz\n\n"
            "Қолдау байланыстары:\n"
            "📞 160 | +7 800 160 00 00\n"
            "📧 Электрондық пошта: telecom@telecom.kz\n\n"
            "Байланыс орталығының жұмыс уақыты:\n"
            "Дс–Жм: 08:00 - 23:00\n"
            "Сб–Жк: 09:00 - 23:00\n"
            "Мереке күндері: 09:00 - 23:00"
        ),

        "en": (
            "We are on social media:\n\n"
            "✈️ Telegram: https://t.me/kazakhtelecom_official\n"
            "📘 Facebook: https://www.facebook.com/telecomkz/\n"
            "🔵 VK: https://vk.com/telecomkz\n"
            "▶️ YouTube: https://www.youtube.com/user/Kazakhtelecom\n"
            "📷 Instagram: https://www.instagram.com/telecomkz/\n"
            "💼 LinkedIn: https://www.linkedin.com/company/kazakhtelecom-jsc\n"
            "🐦 Twitter: https://twitter.com/telecom_kz\n"
            "🌐 Website: https://telecom.kz\n\n"
            "Support contacts:\n"
            "📞 160 | +7 800 160 00 00\n"
            "📧 Email: telecom@telecom.kz\n\n"
            "Call center hours:\n"
            "Mon–Fri: 08:00 - 23:00\n"
            "Sat–Sun: 09:00 - 23:00\n"
            "Holidays: 09:00 - 23:00"
        )
    }

    await message.answer(
        socials_text.get(lang, socials_text["ru"]),
        reply_markup=help_keyboard
    )


@dp.message(Command("language"))
async def cmd_language(message: Message):
    await message.answer(
        "Выберите язык / Тілді таңдаңыз / Choose a language:",
        reply_markup=lang_keyboard
    )


def convert_ogg_to_wav(input_path: str, output_path: str) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@dp.message()
async def handle_message(message: Message) -> None:
    user_id = message.from_user.id
    text = (message.text or "").strip()

    lowered = text.lower()
    if lowered in ("kz", "ru", "en"):
        user_language[user_id] = lowered
        confirm = {
            "ru": "Язык сохранён: 🇷🇺 Русский. Можете задавать вопросы.",
            "kz": "Тіл сақталды: 🇰🇿 Қазақ тілі. Сұрақтарыңызды жазыңыз.",
            "en": "Language set: 🇬🇧 English. You may ask your questions."
        }
        await message.answer(confirm[lowered], reply_markup=help_keyboard)
        return

    if user_id not in user_language:
        await message.answer(
            "Пожалуйста, выберите язык / Тілді таңдаңыз / Please choose a language:",
            reply_markup=lang_keyboard
        )
        return

    lang = user_language[user_id]
    system_prompt = SYSTEM_PROMPTS[lang]

    if message.voice:
        tmp_ogg_path = None
        tmp_wav_path = None
        try:
            file_id = message.voice.file_id
            file_obj = await message.bot.get_file(file_id)
            tg_file_path = file_obj.file_path

            with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as tmp_ogg:
                tmp_ogg_path = tmp_ogg.name
            await message.bot.download_file(tg_file_path, tmp_ogg_path)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                tmp_wav_path = tmp_wav.name

            def _convert_ogg_to_wav_block(in_path, out_path):
                cmd = [
                    "ffmpeg", "-y",
                    "-i", in_path,
                    "-ar", "16000",
                    "-ac", "1",
                    out_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            await asyncio.to_thread(_convert_ogg_to_wav_block, tmp_ogg_path, tmp_wav_path)

            with open(tmp_wav_path, "rb") as audio_file:
                transcription_resp = await asyncio.to_thread(
                    openai_client.audio.transcriptions.create,
                    file=audio_file,
                    model="whisper-1",
                )

            if hasattr(transcription_resp, "text"):
                transcript = transcription_resp.text
            elif isinstance(transcription_resp, dict):
                transcript = transcription_resp.get("text", "")
            else:
                transcript = getattr(transcription_resp, "transcription", "") or ""

            try:
                if tmp_ogg_path:
                    Path(tmp_ogg_path).unlink(missing_ok=True)
                if tmp_wav_path:
                    Path(tmp_wav_path).unlink(missing_ok=True)
            except Exception:
                pass

            if not transcript:
                msgs = {
                    "ru": "Не удалось распознать голос. Попробуйте ещё раз.",
                    "kz": "Дыбысты тану мүмкін болмады. Қайта көріңіз.",
                    "en": "Couldn't transcribe your audio. Please try again."
                }
                await message.answer(msgs[lang], reply_markup=help_keyboard)
                return

            #await message.answer(f"🗣️ {transcript}", reply_markup=help_keyboard)
            user_query_text = transcript

        except subprocess.CalledProcessError:
            logger.exception("ffmpeg conversion error")
            await message.answer({
                "ru": "Ошибка обработки аудио (ffmpeg). Свяжитесь с поддержкой.",
                "kz": "Аудионы өңдеу қатесі (ffmpeg). Қолдауға хабарласыңыз.",
                "en": "Audio processing error (ffmpeg). Please contact support."
            }[lang], reply_markup=help_keyboard)
            return
        except Exception:
            logger.exception("Ошибка при обработке голосового сообщения")
            await message.answer({
                "ru": "Ошибка сервера при обработке голосового сообщения. Попробуйте позже.",
                "kz": "Дауыстық хабарды өңдеу кезінде сервер қатесі. Кейін қайталап көріңіз.",
                "en": "Server error while processing voice message. Try again later."
            }[lang], reply_markup=help_keyboard)
            try:
                if tmp_ogg_path:
                    Path(tmp_ogg_path).unlink(missing_ok=True)
                if tmp_wav_path:
                    Path(tmp_wav_path).unlink(missing_ok=True)
            except Exception:
                pass
            return
    else:
        user_query_text = message.text or ""

    messages = [
        system_prompt,
        {"role": "user", "content": user_query_text}
    ]

    try:
        resp = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=600,
            temperature=0.2,
        )
        assistant_text = ""
        choices = resp.choices if hasattr(resp, "choices") else resp.get("choices", [])
        if choices:
            choice = choices[0]
            if hasattr(choice, "message") and choice.message:
                assistant_text = getattr(choice.message, "content", "") or ""
            elif isinstance(choice, dict):
                assistant_text = (choice.get("message", {}) or {}).get("content", "") or choice.get("text", "") or ""
            else:
                assistant_text = getattr(choice, "text", "") or ""
        else:
            assistant_text = ""
    except Exception:
        logger.exception("Ошибка OpenAI")
        assistant_text = {
            "ru": "Ошибка сервера. Повторите позже.",
            "kz": "Сервер қатесі. Кейінірек қайталап көріңіз.",
            "en": "Server error. Please try again later."
        }[lang]

    cleaned = clean_markdown(assistant_text)
    try:
        await message.answer(cleaned or assistant_text, parse_mode="Markdown", reply_markup=help_keyboard)
    except Exception:
        await message.answer(assistant_text, reply_markup=help_keyboard)

    tmp_mp3_path = None
    tmp_oggopus_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
            tmp_mp3_path = tmp_mp3.name

        def _create_tts_file(path, text_to_say, voice):
            resp = openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text_to_say,
            )
            if hasattr(resp, "stream_to_file"):
                resp.stream_to_file(path)
                return
            content = getattr(resp, "content", None)
            if content and isinstance(content, (bytes, bytearray)):
                with open(path, "wb") as f:
                    f.write(content)
                return
            if isinstance(resp, dict):
                for key in ("audio", "audio_base64", "data"):
                    if key in resp:
                        data = resp[key]
                        if isinstance(data, str):
                            try:
                                import base64
                                b = base64.b64decode(data)
                                with open(path, "wb") as f:
                                    f.write(b)
                                return
                            except Exception:
                                pass
                        elif isinstance(data, (bytes, bytearray)):
                            with open(path, "wb") as f:
                                f.write(data)
                            return
            raise RuntimeError("Unsupported TTS response format")

        voice_map = {"ru": "alloy", "kz": "alloy", "en": "alloy"}
        tts_voice = voice_map.get(lang, "alloy")

        await asyncio.to_thread(_create_tts_file, tmp_mp3_path, assistant_text or cleaned or " ", tts_voice)

        with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as tmp_oggopus:
            tmp_oggopus_path = tmp_oggopus.name

        def _convert_mp3_to_oggopus(in_path, out_path):
            cmd = [
                "ffmpeg", "-y",
                "-i", in_path,
                "-c:a", "libopus",
                "-b:a", "64k",
                out_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        await asyncio.to_thread(_convert_mp3_to_oggopus, tmp_mp3_path, tmp_oggopus_path)

        audio_input = FSInputFile(tmp_oggopus_path)
        try:
            await message.answer_voice(voice=audio_input, reply_markup=help_keyboard)
        except Exception:
            audio_input_mp3 = FSInputFile(tmp_mp3_path)
            try:
                await message.answer_audio(audio=audio_input_mp3, reply_markup=help_keyboard)
            except Exception:
                await message.answer_document(document=audio_input_mp3, caption="Audio reply", reply_markup=help_keyboard)

    except Exception:
        logger.exception("Ошибка TTS / отправки аудио")
        try:
            error_msg = {
                "ru": "Не удалось сгенерировать голосовой ответ, отправляю только текст.",
                "kz": "Дауыстық жауапты жасау мүмкін болмады, тек мәтін жіберілді.",
                "en": "Could not generate voice reply, sending text only."
            }[lang]
            await message.answer(error_msg, reply_markup=help_keyboard)
        except Exception:
            pass
    finally:
        try:
            if tmp_mp3_path:
                Path(tmp_mp3_path).unlink(missing_ok=True)
            if tmp_oggopus_path:
                Path(tmp_oggopus_path).unlink(missing_ok=True)
        except Exception:
            pass


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
