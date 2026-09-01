# Automated Voice QA Agent

A Python voice bot that places real outbound phone calls and holds natural,
multi-turn spoken conversations with a target conversational AI system, in
order to test it for bugs and quality issues. Built for the Pretty Good AI
AI Engineering Challenge, testing their voice agent for Pivot Point
Orthopedics.

The bot plays one of several simulated "patient" personas (scheduling,
rescheduling, prescription refills, insurance/hours questions, and
deliberately ambiguous or interruption-heavy callers), has a real spoken
conversation with the target system, and records/transcribes the call for
review.

## Architecture at a glance

Twilio (telephony) → Deepgram (speech-to-text) → OpenAI GPT-4o-mini
(decides the patient's next line) → Cartesia (text-to-speech) → Twilio,
in a real-time loop orchestrated by Pipecat. See `ARCHITECTURE.md` for
the full reasoning behind these choices.

## Prerequisites

- Python 3.11 (3.14 will fail to install `numpy` — see note below)
- Accounts + API keys for: Twilio, Deepgram, OpenAI, Cartesia
- [ngrok](https://ngrok.com) installed and authenticated (for local
  development — exposes your local server to Twilio's webhooks)

**Note on Python version:** this project depends on `pipecat-ai`, which
requires `numpy==1.26.4`. That version has no pre-built installer for
Python 3.14, so `pip install` will try to compile it from source and fail
without a C compiler. Use Python 3.11 or 3.12 instead.

## Setup

1. Clone this repo and enter the folder:
   ```
   git clone https://github.com/Sahithi102302/voice-agent-qa.git
   cd voice-agent-qa
   ```

2. Create a virtual environment using Python 3.11 specifically:
   ```
   py -3.11 -m venv venv
   venv\Scripts\activate        (Windows)
   source venv/bin/activate     (macOS/Linux)
   ```

3. Install dependencies:
   ```
   py -m pip install -r requirements.txt
   ```

4. Copy the environment template and fill in your real credentials:
   ```
   copy .env.example .env        (Windows)
   cp .env.example .env          (macOS/Linux)
   ```
   Edit `.env` and fill in your Twilio Account SID, Auth Token, Twilio
   phone number, Deepgram/OpenAI/Cartesia API keys, and the target phone
   number.

5. Start ngrok in its own terminal, tunneling to port 8000:
   ```
   ngrok http 8000
   ```
   Copy the `https://...ngrok-free.app` (or `.dev`) URL it gives you and
   set it as `PUBLIC_BASE_URL` in `.env`. **This URL changes every time
   you restart ngrok on the free tier — update `.env` each time.**

## How to run

You need three things running at once, each in its own terminal:

**Terminal 1 — the server** (stays running):
```
uvicorn src.server:app --reload --port 8000
```

**Terminal 2 — ngrok** (stays running):
```
ngrok http 8000
```

**Terminal 3 — place a call** (run this each time you want to place one):
```
py -m src.call_runner <persona>
```
Replace `<persona>` with one of: `scheduling`, `reschedule`, `refill`,
`insurance_hours`, `vague_request`, `interruption_heavy`,
`first_time_caller`, `impossible_request`, `contradictory_info`. If
omitted, defaults to `scheduling`.

Example:
```
py -m src.call_runner refill
```

The call is placed to `TARGET_PHONE_NUMBER` in `.env`. Twilio records the
call automatically; recordings can be downloaded from the Twilio Console
under Monitor → Logs → Calls.

## Project structure

```
voice-agent-qa/
├── src/
│   ├── server.py          FastAPI webhook + WebSocket server Twilio talks to
│   ├── bot.py              The Pipecat pipeline (STT -> LLM -> TTS)
│   ├── personas.py         Patient scenario scripts (the "who" and "why" for each call)
│   └── call_runner.py      Places outbound calls via Twilio's REST API
├── recordings/              Downloaded MP3 recordings of real test calls
├── transcripts/             Clean text transcripts matching each recording
├── bug_report.md            Documented issues found in the target system
├── ARCHITECTURE.md          Design decisions and reasoning
├── requirements.txt
└── .env.example             Template of required environment variables
```

## Output

Each real test call produces a Twilio-hosted recording (downloaded
manually into `recordings/`) and a corresponding transcript in
`transcripts/`, named `call-NN-<persona>.mp3` / `.txt`.

## Known limitations

- The ngrok free tier generates a new public URL on every restart,
  requiring a manual `.env` update each time.
- Average LLM response latency is ~1.3 seconds after switching from
  GPT-4o to GPT-4o-mini (see `ARCHITECTURE.md` for the benchmarking
  behind this decision) — still slightly higher than ideal for a fully
  seamless phone conversation.