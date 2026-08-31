"""
server.py — Step 1: "Hello World" webhook server

WHAT THIS FILE DOES:
Twilio calls this server the moment a phone call connects, and expects
a response written in TwiML (Twilio's XML instruction format) telling
it what to do next. Right now, we only tell it to speak one sentence
and hang up — no AI is involved yet.

WHY THIS STEP EXISTS:
Before wiring up speech-to-text, an LLM, and text-to-speech, we want to
prove the basic plumbing works: Twilio can reach this server (through
the ngrok tunnel), and real audio plays on the call.

HOW TO RUN:
    uvicorn src.server:app --reload --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI()


@app.post("/voice")
async def voice_webhook(request: Request):
    """
    Twilio sends a POST request here as soon as the call connects.
    We must reply with TwiML (XML) — not JSON or plain text.

    <Say> uses Twilio's built-in text-to-speech (NOT Cartesia — that
    comes later in Step 4). This is purely to confirm audio flows.
    """
    twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">
        Hello! This is a test call from my voice bot project.
        If you can hear this clearly, the connection is working.
        Goodbye.
    </Say>
</Response>"""

    return Response(content=twiml_response, media_type="application/xml")


@app.get("/")
async def health_check():
    """
    Visit this URL in a browser to confirm the server is running.
    Not used by Twilio — just a manual sanity check for you.
    """
    return {"status": "voicebot server is running"}