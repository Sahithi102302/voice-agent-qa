"""
call_runner.py — places outbound calls, with a chosen persona

WHAT THIS FILE DOES:
Uses Twilio's REST API to dial a phone number, telling it which patient
persona to use for this call (passed through as a URL query parameter
that server.py reads and forwards to bot.py).

HOW TO RUN:
    py -m src.call_runner scheduling
    py -m src.call_runner reschedule
    py -m src.call_runner refill
    py -m src.call_runner insurance_hours
    py -m src.call_runner vague_request
    py -m src.call_runner interruption_heavy

If no persona is given, defaults to "scheduling".

BEFORE RUNNING:
    1. server.py must already be running (separate terminal)
    2. ngrok must already be running and tunneling to the same port
    3. PUBLIC_BASE_URL in .env must match your CURRENT ngrok URL
       (it changes every time you restart ngrok on the free tier)
"""

import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

# ------------------------------------------------------------------
# Load credentials and settings from .env
# ------------------------------------------------------------------
ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
FROM_NUMBER = os.environ["TWILIO_PHONE_NUMBER"]
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"]
TO_NUMBER = os.environ["TARGET_PHONE_NUMBER"]


def place_call(persona: str):
    """Places one outbound call using the given persona, and prints the result."""
    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    # Pass the chosen persona as a query parameter on the webhook URL.
    # Twilio forwards this straight through to our /voice endpoint.
    voice_url = f"{PUBLIC_BASE_URL}/voice?persona={persona}"

    call = client.calls.create(
        to=TO_NUMBER,
        from_=FROM_NUMBER,
        url=voice_url,  # Twilio POSTs here once the call connects
        record=True,
    )

    print(f"Call placed successfully. SID: {call.sid}")
    print(f"Persona: {persona}")
    print(f"Calling the real target number: {TO_NUMBER}")


if __name__ == "__main__":
    chosen_persona = sys.argv[1] if len(sys.argv) > 1 else "scheduling"
    place_call(chosen_persona)