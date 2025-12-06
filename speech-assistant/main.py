import os
import json
import base64
import asyncio
import aiohttp
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PORT = int(os.getenv('PORT', 5050))
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.2))

if not OPENAI_API_KEY:
    raise ValueError("Не задан OPENAI_API_KEY в .env")

SYSTEM_PROMPT_RU = (
    "Ты — официальный цифровой помощник АО «Қазақтелеком» (Kazakhtelecom JSC). "
    "Кратко, вежливо и профессионально отвечай на вопросы на русском языке.\n\n"
    "Правила ответа:\n"
    "• Отвечай кратко, по делу и дружелюбно.\n"
    "• Если вопрос требует действий специалиста (выезд мастера, операции с лицевым счётом, личные данные), "
    "перенаправляй в онлайн-каналы (+77080000160) или контакт-центр 160 и указывай возможные сроки/стоимость, если известно.\n"
)

VOICE = "alloy"

LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created', 'session.updated'
]

app = FastAPI()

@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "Kazakhtelecom realtime media server (русский) running!"}


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    response = VoiceResponse()
    response.say("Пожалуйста, подождите, мы соединяем вас с голосовым помощником Казахтелеком. После сигнала говорите.", language="ru-RU")
    response.pause(length=1)

    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f"wss://{host}/media-stream")
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    print("Twilio client connected to /media-stream")

    openai_url = f"wss://api.openai.com/v1/realtime?model=gpt-realtime&temperature={TEMPERATURE}"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    session = aiohttp.ClientSession()
    try:
        print("Connecting to OpenAI Realtime WS...")
        openai_ws = await session.ws_connect(openai_url, headers=headers, timeout=30)
    except Exception as e:
        print("Не удалось подключиться к OpenAI Realtime WebSocket:", repr(e))
        await websocket.close()
        await session.close()
        return

    try:
        session_update = {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "model": "gpt-realtime",
                "output_modalities": ["audio"],
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcmu"},
                        "turn_detection": {"type": "server_vad"}
                    },
                    "output": {
                        "format": {"type": "audio/pcmu"},
                        "voice": VOICE
                    }
                },
                "instructions": SYSTEM_PROMPT_RU
            }
        }
        await openai_ws.send_str(json.dumps(session_update))
        print("Sent session.update to OpenAI")

        stream_sid = None
        latest_media_timestamp = 0
        last_assistant_item = None
        mark_queue = []
        response_start_timestamp_twilio = None

        async def receive_from_twilio():
            nonlocal stream_sid, latest_media_timestamp
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    evt = data.get("event")
                    if evt == "media":
                        latest_media_timestamp = int(data['media'].get('timestamp', 0))
                        audio_payload = data['media']['payload']
                        audio_append = {"type": "input_audio_buffer.append", "audio": audio_payload}
                        await openai_ws.send_str(json.dumps(audio_append))
                    elif evt == "start":
                        stream_sid = data['start'].get('streamSid')
                        print("Stream started:", stream_sid)
                    elif evt == "mark":
                        if mark_queue:
                            mark_queue.pop(0)
            except WebSocketDisconnect:
                print("Twilio disconnected (receive)")
            except Exception as e:
                print("Error in receive_from_twilio:", repr(e))

        async def send_to_twilio():
            nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio
            try:
                async for msg in openai_ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            response = json.loads(msg.data)
                        except Exception:
                            continue

                        if response.get('type') in LOG_EVENT_TYPES:
                            print("OpenAI event:", response.get('type'))

                        if response.get('type') == 'response.output_audio.delta' and 'delta' in response:
                            try:
                                audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                            except Exception:
                                audio_payload = response['delta']

                            audio_delta = {"event": "media", "streamSid": stream_sid, "media": {"payload": audio_payload}}
                            await websocket.send_json(audio_delta)

                            if response.get("item_id") and response["item_id"] != last_assistant_item:
                                response_start_timestamp_twilio = latest_media_timestamp
                                last_assistant_item = response["item_id"]
                                mark_queue.append('responsePart')
                                await send_mark(websocket, stream_sid)

                        if response.get('type') == 'input_audio_buffer.speech_started':
                            print("Caller speech started (OpenAI event)")
                            if last_assistant_item:
                                await handle_speech_started_event()

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print("OpenAI WS error:", openai_ws.exception())
                        break
            except Exception as e:
                print("Error in send_to_twilio main loop:", repr(e))

        async def handle_speech_started_event():
            nonlocal response_start_timestamp_twilio, last_assistant_item
            print("Handling speech started (interruption).")
            if mark_queue and response_start_timestamp_twilio is not None:
                elapsed_time = latest_media_timestamp - response_start_timestamp_twilio
                if last_assistant_item:
                    truncate_event = {
                        "type": "conversation.item.truncate",
                        "item_id": last_assistant_item,
                        "content_index": 0,
                        "audio_end_ms": elapsed_time
                    }
                    await openai_ws.send_str(json.dumps(truncate_event))

                await websocket.send_json({"event": "clear", "streamSid": stream_sid})
                mark_queue.clear()
                last_assistant_item = None
                response_start_timestamp_twilio = None

        async def send_mark(connection, stream_sid_local):
            if stream_sid_local:
                mark_event = {"event": "mark", "streamSid": stream_sid_local, "mark": {"name": "responsePart"}}
                await connection.send_json(mark_event)

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

    finally:
        try:
            await openai_ws.close()
        except Exception:
            pass
        await session.close()
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    print("Starting Kazakhtelecom realtime media server (RU) on port", PORT)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
