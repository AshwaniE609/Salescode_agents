import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import threading

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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("realtime-video-agent")

# Environment
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Global session
_global_session = None

# FastAPI app
app = FastAPI()

class FillerWordsUpdate(BaseModel):
    words: list[str]
    action: str

@app.post("/api/filler-words")
async def update_filler_words(update: FillerWordsUpdate):
    if _global_session is None:
        raise HTTPException(status_code=503, detail="Session not initialized")
    
    if update.action == "add":
        _global_session.add_filler_words(update.words)
        return {"status": "added", "count": len(update.words)}
    elif update.action == "remove":
        _global_session.remove_filler_words(update.words)
        return {"status": "removed", "count": len(update.words)}
    elif update.action == "replace":
        _global_session.set_filler_words(update.words)
        return {"status": "replaced", "count": len(update.words)}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

@app.get("/api/filler-words")
async def get_filler_words():
    if _global_session is None:
        raise HTTPException(status_code=503, detail="Session not initialized")
    return {"filler_words": list(_global_session.get_filler_words())}

def run_api_server():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

async def entrypoint(ctx: JobContext):
    global _global_session
    
    multilingual_fillers = [
        'uh', 'um', 'umm', 'hmm', 'ah', 'oh', 'huh', 'hm',
        'mhm', 'mmhmm', 'mm', 'mmm', 'uhuh',
        'er', 'erm', 'uhh', 'uhm',
        'yeah', 'yep', 'yup', 'yes', 'aha', 'mhmm',
        'uh huh', 'mm hmm', 'uh-huh', 'mm-hmm',
        'हम्म', 'उम', 'अह', 'हां', 'हाँ', 'हम', 'उह', 'ठीक',
        'હમ્મ', 'ઉમ', 'અહ',
        'haan', 'han', 'theek', 'acha',
        'like', 'you know', 'i mean',
    ]
    
    logger.info(f"Loaded {len(multilingual_fillers)} filler words for filtering")
    
    session = AgentSession(
        vad=silero.VAD.load(),
        llm=google.realtime.RealtimeModel(),
        _ignored_filler_words=multilingual_fillers,
    )
    
    _global_session = session
    
    # START API SERVER HERE
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    logger.info("🌐 API server started on http://localhost:8000")
    
    agent = Agent(
        instructions="You are a helpful AI assistant. Keep responses clear and a medium size response.",
    )
    
    @session.on("user_input_transcribed")
    def on_transcript(event):
        logger.info("user transcript", extra={"transcript": event.transcript, "is_final": event.is_final})
    
    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(video_enabled=False),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )
    
    try:
        await session.generate_reply(instructions="Greet the user and ask how you can help")
    except Exception as e:
        logger.error(f"Failed to generate greeting: {e}")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
