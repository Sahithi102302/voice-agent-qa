# Architecture

## Pipeline diagram

```
                     Twilio                          Pretty Good AI
   ┌──────────────┐  places call  ┌────────────────┐  (target agent,
   │ call_runner  │──────────────>│    Twilio      │<─────────────────>
   │   .py        │               │  (telephony)   │   live phone call
   └──────────────┘               └───────┬────────┘
                                           │ bidirectional
                                           │ WebSocket audio
                                           v
                                  ┌────────────────┐
                                  │  server.py     │  (FastAPI, exposed
                                  │  /voice /ws    │   via ngrok tunnel)
                                  └───────┬────────┘
                                          │
                                          v
                                  ┌────────────────┐
                                  │   bot.py       │  (Pipecat pipeline)
                                  │                │
        agent audio  ───────────>│  Deepgram STT  │
                                  │       │        │
                                  │       v        │
                                  │ GPT-4o-mini    │<── personas.py
                                  │ (patient logic)│    (which character
                                  │       │        │     to play)
                                  │       v        │
        patient audio <──────────│ Cartesia TTS   │
                                  └────────────────┘
```

## How it works

The bot places an outbound call via Twilio's REST API (`call_runner.py`),
which connects to a locally-running FastAPI server (exposed to the
internet via ngrok during development). When the call connects, Twilio
opens a bidirectional WebSocket audio stream to the server. That audio
flows through a real-time pipeline orchestrated by Pipecat: Deepgram
transcribes the target agent's speech to text, OpenAI's GPT-4o-mini
generates the next line for the bot's "patient" persona based on the
conversation so far, and Cartesia converts that reply back into speech,
which is streamed back into the live call. Pipecat's built-in voice
activity detection and turn-taking logic handle knowing when the other
party has actually finished speaking, so the bot doesn't talk over the
target agent or respond to mid-sentence pauses. Each patient persona (a
distinct name, backstory, and goal — e.g., scheduling a follow-up,
requesting a refill, or a deliberately vague or urgent caller) lives as
a separate system prompt in `personas.py`, selected per call via a
Twilio Custom Parameter passed through the call's TwiML.

## Key design decisions

**Pipecat pipeline over a bundled Realtime API.** I considered using a
single-vendor bundled voice-agent product (e.g., Deepgram's own Voice
Agent API, or OpenAI's Realtime API, both of which combine STT/LLM/TTS
into one managed service) instead of assembling the pipeline myself.
The bundled approach would have been faster to build, but it hands the
orchestration logic (turn-taking, conversation state) to a vendor's
black box rather than code I control and can explain in detail. Since
this project's value is partly in demonstrating system design and
debugging ability, I chose the assembled-pipeline approach: more setup
cost, but a more legible, customizable system, and better material for
explaining concrete technical tradeoffs and iterating on specific
components (e.g., swapping the LLM independently of STT/TTS).

**GPT-4o-mini over GPT-4o.** I initially built the pipeline with full
GPT-4o and measured average response latency (time from the target
agent finishing speech to the bot beginning its reply) at ~3.9 seconds
across a real test conversation — noticeably slow for natural phone
dialogue. Since the persona's task (short, in-character conversational
replies following a simple, fixed backstory) doesn't require deep
reasoning, I benchmarked the same conversation script against
GPT-4o-mini and measured ~1.3 seconds average latency — a ~65%
reduction — with no observable drop in response coherence or
persona consistency across 13 real test calls. GPT-4o-mini was used for
all subsequent testing.

**Twilio Custom Parameters over URL query strings for persona
selection.** My first implementation passed the chosen persona as a
query string on the Media Stream's WebSocket URL (`/ws?persona=refill`).
This silently failed — Twilio's `<Stream>` element does not support
query string parameters on its `url` attribute, and strips them without
an explicit error. I found this in Twilio's own documentation after the
bug manifested as every call defaulting to the same persona regardless
of what was requested. The fix was to use Twilio's supported "Custom
Parameters" mechanism (`<Parameter>` tags nested inside `<Stream>`),
which Twilio delivers via the WebSocket's initial "start" message
instead of the connection URL.

**Nine distinct personas rather than a handful of near-duplicates.**
Beyond the task's core scenario types (scheduling, rescheduling,
refills, hours/insurance), I added personas targeting specific failure
dimensions I hadn't yet tested: an urgent/out-of-scope request (to test
safety-relevant triage behavior) and a caller who self-corrects
mid-call (to test whether the agent registers a live correction rather
than just its first-heard value). This was a deliberate choice to
maximize the diversity of system behavior surfaced per call, rather
than repeating similar scenarios for volume.

## Notable technical issues encountered and resolved

- A `numpy` build failure traced to Python 3.14 lacking a pre-built
  wheel for the pinned version `pipecat-ai` requires — resolved by
  rebuilding the virtual environment on Python 3.11.
- An incorrect `pipecat-ai` package extras specification (`[twilio,
  websockets]`, neither of which exist in the current package version)
  caused `pip` to silently resolve to a version of `pipecat-ai` over a
  year out of date, missing the APIs the code depended on — resolved by
  correcting the extras to match the package's actual current interface
  (`[silero,deepgram,cartesia,openai,websocket,runner]`).
- A Python module-caching bug: reading the selected persona at module
  import time (rather than per-call) meant only the first persona
  requested in a given server session was ever actually used, regardless
  of what later calls requested — resolved by moving the persona lookup
  inside the per-call function and passing it explicitly as a parameter.
- A port conflict with an unrelated previous project left running on
  the same local port, causing Twilio requests to reach the wrong
  server and return 404s — resolved by identifying and terminating the
  stale process.

## Alternatives considered

A fully bundled voice-agent platform (e.g., Vapi, Retell, OpenAI's
Realtime API) was considered as a faster path to a working demo, at the
cost of less visibility into and control over the underlying pipeline.
Given the goal of demonstrating system design reasoning, the assembled
Twilio + Pipecat approach was judged the better fit despite its longer
setup time.

## Key findings summary

Testing surfaced one critical-severity finding (no urgency triage for
acute patient requests) and one high-severity, root-caused finding (a
reproducible patient-record lookup failure isolated to phone numbers
with prior conflicting call history, confirmed via controlled testing
against a fresh-identity control case). See `bug_report.md` for full
details, transcripts, and recordings.