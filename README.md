
# IT-FEST-2025 — Kazakhtelecom Voice & Chatbot

Краткое описание
----------------
Проект — Telegram-бот для АО «Қазақтелеком». Бот поддерживает выбор языка (kk/ru/en), текстовый и голосовой ввод, распознавание речи (Whisper), генерацию ответов через OpenAI и синтез речи (TTS). Отвечает коротко и профессионально, при необходимости предлагает обратиться в контакт-центр.

Функции
-------
- Выбор языка интерфейса (kk / ru / en)
- Текстовый диалог с моделью OpenAI
- Голосовой ввод: распознавание OGG → WAV → Whisper
- Голосовой ответ: TTS → MP3 → OGG/OPUS и отправка как голосовое сообщение
- Быстрые команды: `/start`, `/help`, `/language`, `/socials`

Требования
----------
- Python 3.10+ (рекомендуется 3.11)
- ffmpeg (в системном PATH)
- Virtual environment
- Токены в `.env`: `BOT_TOKEN`, `OPENAI_API_KEY`, `OPENAI_MODEL` (опционально)

Пример `.env`
```
BOT_TOKEN=123456:ABC-DEF...
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Установка (Linux / WSL / macOS)
-------------------------------
```bash
# в каталоге проекта
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# установи зависимости (создай requirements.txt, например ниже)
pip install aiogram openai python-dotenv
# убедись, что ffmpeg установлен:
# Ubuntu / Debian:
sudo apt update && sudo apt install -y ffmpeg
# заполни .env и запусти
python bot.py
```

Установка (Windows PowerShell)
-----------------------------
```powershell
# в каталоге проекта
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install aiogram openai python-dotenv
# установить ffmpeg (рекомендуется через choco или ручная установка)
# если установлен Chocolatey:
choco install ffmpeg -y
# заполните .env и запустите
python bot.py
```

requirements.txt (пример)
-------------------------
```
aiogram==3.0.0
openai==1.0.0
python-dotenv
```
> Примечание: версии пакетов могут отличаться — подбери версии под свою среду.

Запуск
-----
1. Активировать виртуальное окружение.
2. Убедиться, что `.env` заполнен.
3. Выполнить `python bot.py`.

Советы и отладка
----------------
- Логи: запускай в терминале — ошибки и успешные запросы OpenAI видны в логах.
- Проблемы с TTS/Whisper: проверь актуальность OpenAI SDK и формат запроса; можно переключиться на отправку/получение raw-байтов.
- ffmpeg: критичен для конверсии audio → ogg/opus. Убедитесь, что `ffmpeg` в PATH.
- Если бот не видит токены из `.env`, убедитесь, что вы выполнили `load_dotenv()` и файл `.env` находится рядом с `bot.py`.

Лицензия
--------
MIT

Контакты
--------
Проект — IT-FEST-2025. Для вопросов по коду — оставь issue в репозитории.
