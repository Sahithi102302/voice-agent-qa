"""
bot.py — Step 4: the real AI pipeline

WHAT THIS FILE DOES:
This is where the actual "patient brain" lives. It wires together four
services into one live, real-time loop:

    Twilio audio in -> Deepgram (speech-to-text) -> GPT-4o-mini (decides reply)
    -> Cartesia (text-to-speech) -> Twilio audio out

Pipecat manages the real-time choreography (knowing when the other side
has finished talking, streaming audio without awkward gaps, etc.) so we
don't have to write that timing logic ourselves.

WHY THIS SPECIFIC STRUCTURE:
This follows Pipecat's own current official pattern for Twilio outbound
calls (verified against their live example repo), adapted to use OpenAI
GPT-4o-mini instead of their demo's default LLM, and with our own
"patient" persona instead of a generic assistant.

PERSONA SELECTION:
Twilio's <Stream> url does not support query string parameters (a
documented Twilio limitation) — so the chosen persona is sent as a
Twilio "Custom Parameter" instead (see the <Parameter> tag in
server.py's /voice route). Twilio includes that value in the WebSocket
"start" message it sends once the stream connects. parse_telephony_websocket()
(called once, right here in bot()) parses that message into call_data,
and we read the persona out of call_data["body"]. This value is then
passed directly into run_bot() as a function argument — no environment
variables, no URL tricks.
"""

import os

from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments, WebSocketRunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.workers.runner import WorkerRunner

from .personas import PERSONAS


async def run_bot(transport: BaseTransport, handle_sigint: bool, persona_key: str):
    """
    Builds and runs the actual conversation pipeline once a call is connected.

    persona_key: which entry in PERSONAS (personas.py) to use as this
    call's patient persona. Passed in directly by bot(), which already
    extracted it from Twilio's Custom Parameters.
    """
    patient_system_prompt = PERSONAS[persona_key]
    logger.info(f"Using persona: {persona_key}")

    # --- Speech-to-text: converts the agent's spoken audio into text ---
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    # --- The "brain": decides what the patient says next ---
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
        settings=OpenAILLMService.Settings(
            system_instruction=patient_system_prompt,
        ),
    )

    # --- Text-to-speech: converts the LLM's reply into spoken audio ---
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        settings=CartesiaTTSService.Settings(
            # This is one of Cartesia's built-in voice IDs (a natural-sounding
            # female voice). We can swap this later once we've listened to it.
            voice="71a7ad14-091c-4e8e-a314-022ece01c121",
        ),
    )

    # --- Conversation memory: keeps track of the back-and-forth so far ---
    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            # Silero VAD detects when the other person has actually
            # stopped talking (not just paused), so our bot doesn't
            # jump in too early or too late.
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    # --- The actual pipeline: defines the order data flows through ---
    pipeline = Pipeline(
        [
            transport.input(),      # audio coming IN from the phone call
            stt,                    # turn that audio into text
            user_aggregator,        # remember what the agent said
            llm,                    # decide the patient's reply
            tts,                    # turn that reply into audio
            transport.output(),     # send audio OUT to the phone call
            assistant_aggregator,   # remember what our patient said
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            # Twilio streams audio at 8kHz — matching this exactly avoids
            # unnecessary audio resampling, which can introduce artifacts.
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # We deliberately do NOT make the bot speak first here.
        # In a real call, Pretty Good AI's agent will greet first
        # ("Thanks for calling..."), and our patient responds naturally
        # to that — just like a real phone call.
        logger.info("Call connected — waiting for the other side to speak first")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Call ended")
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=handle_sigint)
    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """
    Entry point called once per call. Sets up the Twilio-specific
    transport (the audio serializer that speaks Twilio's WebSocket
    protocol), extracts the chosen persona from Twilio's Custom
    Parameters, then hands off to run_bot() to do the actual conversation.
    """
    transport_type, call_data = await parse_telephony_websocket(runner_args.websocket)
    logger.info(f"Detected transport: {transport_type}")

    # Twilio sends our custom "persona" parameter (set via <Parameter> in
    # server.py's TwiML) inside the parsed "start" message body — NOT as
    # a URL query string, since Twilio's <Stream> url doesn't support those.
    persona_key = call_data.get("body", {}).get("persona", "scheduling")

    serializer = TwilioFrameSerializer(
        stream_sid=call_data["stream_id"],
        call_sid=call_data["call_id"],
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
    )

    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    await run_bot(transport, runner_args.handle_sigint, persona_key)