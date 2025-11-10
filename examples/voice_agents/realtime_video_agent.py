import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    RoomOutputOptions,
    WorkerOptions,
    cli,
)
from livekit.plugins import google, silero

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("realtime-video-agent")

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


async def entrypoint(ctx: JobContext):
    # UPDATED: Complete filler list with "yes", "aha", etc.
    multilingual_fillers = [
        # English - basic
        'uh', 'um', 'umm', 'hmm', 'ah', 'oh', 'huh', 'hm',
        # English - extended variations
        'mhm', 'mmhmm', 'mm', 'mmm', 'uhuh',
        'er', 'erm', 'uhh', 'uhm',
        # English - affirmatives (often used as fillers)
        'yeah', 'yep', 'yup', 'yes', 'aha', 'mhmm',  # ✅ ADDED
        'uh huh', 'mm hmm', 'uh-huh', 'mm-hmm',
        
        # Hindi (Devanagari script)
        'हम्म', 'उम', 'अह', 'हां', 'हाँ', 'हम', 'उह', 'ठीक',
        
        # Gujarati
        'હમ્મ', 'ઉમ', 'અહ',
        
        # Romanized Hindi/Urdu
        'haan', 'han', 'theek', 'acha',
        
        # Conversational fillers
        'like', 'you know', 'i mean',
    ]
    
    logger.info(f"Loaded {len(multilingual_fillers)} filler words for filtering")
    
    session = AgentSession(
        vad=silero.VAD.load(),
        llm=google.realtime.RealtimeModel(),
        ignored_filler_words=multilingual_fillers,
    )
    
    # ... rest of your code ...


    agent = Agent(
        instructions="You are a helpful AI assistant. Keep responses clear and concise.",
    )

    # Event listeners for visibility
    @session.on("user_input_transcribed")
    def on_transcript(event):
        logger.info(
            "user transcript",
            extra={
                "transcript": event.transcript,
                "is_final": event.is_final
            }
        )
    
    @session.on("agent_started_speaking")
    def on_agent_start():
        logger.info("🗣️ Agent started speaking - filler filtering ACTIVE")
    
    @session.on("agent_stopped_speaking")
    def on_agent_stop():
        logger.info("🔇 Agent stopped speaking - filler filtering INACTIVE")

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(video_enabled=False),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )

    await session.generate_reply(
        instructions="Greet the user and ask how you can help"
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
