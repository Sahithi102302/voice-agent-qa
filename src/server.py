"""
server.py — Step 4: webhook + WebSocket server

WHAT CHANGED FROM STEP 1:
Previously, /voice replied with <Say> (one fixed sentence, no listening).
Now /voice replies with <Connect><Stream>, telling Twilio to open a live
WebSocket connection to our /ws endpoint instead — that's where the real
AI conversation actually happens, handled by bot.py.

PERSONA ROUTING:
Twilio's <Stream> element does NOT support query string parameters on
its url attribute (Twilio silently strips them) — this is a documented
Twilio limitation, confirmed against their own docs. So we pass the
chosen persona using Twilio's supported "Custom Parameters" mechanism
instead: a nested <Parameter> tag inside <Stream>. Twilio then includes
that value in the WebSocket "start" message it sends once the stream
connects — bot.py reads it from there (see bot.py's `bot()` function),
not from any URL query string on the WebSocket side.
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from loguru import logger

load_dotenv()

app = FastAPI()


@app.post("/voice")
async def voice_webhook(request: Request) -> HTMLResponse:
    """
    Twilio hits this the moment a call connects. We tell it to open a
    live audio stream to /ws, and pass the chosen persona as a Twilio
    Custom Parameter (via the nested <Parameter> tag), since <Stream>'s
    url attribute cannot carry query string parameters.
    """
    public_base_url = os.environ["PUBLIC_BASE_URL"]
    persona = request.query_params.get("persona", "scheduling")

    # NOTE: no ?persona=... appended here — the Stream url must be bare.
    ws_url = public_base_url.replace("https://", "wss://") + "/ws"

    twiml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="persona" value="{persona}" />
        </Stream>
    </Connect>
</Response>"""

    logger.info(f"Serving TwiML — persona={persona}, connecting call to {ws_url}")
    return HTMLResponse(content=twiml_content, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Twilio opens a WebSocket connection here once /voice tells it to.
    This is where the actual audio streaming and AI pipeline run for
    the entire duration of the call.

    We deliberately do NOT parse the persona here — bot.py's own
    parse_telephony_websocket() call (inside the bot() function) is
    where Twilio's "start" message (including our custom "persona"
    parameter) gets read, exactly once. Parsing it a second time here
    would consume that message and break bot.py's own parsing.
    """
    from .bot import bot
    from pipecat.runner.types import WebSocketRunnerArguments

    await websocket.accept()
    logger.info("WebSocket connection accepted — starting bot")

    try:
        runner_args = WebSocketRunnerArguments(websocket=websocket)
        await bot(runner_args)
    except Exception as e:
        logger.error(f"Error during call: {e}")
        await websocket.close()


@app.get("/")
async def health_check():
    return {"status": "voicebot server is running"}