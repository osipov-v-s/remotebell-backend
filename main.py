import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path

import pygame
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from models.requests.AudioRequest import AudioRequest

from models.requests.Event import Event
from services.ScheduleService import ScheduleService, SCHEDULES_PATH, AUDIO_DIR


try:
    pygame.mixer.init()
    SOUND_AVAILABLE = True
    print("Sound initialized successfully")
except Exception as e:
    SOUND_AVAILABLE = False
    print(f"Warning: Sound not available (running in silent mode): {e}")

scheduleService = ScheduleService(SCHEDULES_PATH, AUDIO_DIR)

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR/"schedule_service.log", encoding="UTF-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Load schedule service...")
    task = asyncio.create_task(scheduleService.run())
    logger.info("task is running")
    yield
    task.cancel()
    if SOUND_AVAILABLE:
        pygame.mixer.music.stop()
    logger.info("Schedule service stopped")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/audio", StaticFiles(directory="audio"))

current_playing = None
is_playing = False
schedules_path = "schedules/schedules.json"



@app.get("/api/audio-files")
async def get_audio_files():
    audio_dir = "audio"
    files = os.listdir(audio_dir)
    audio_files = [f for f in files if f.endswith(("mp3", ".wav", ".ogg", ".m4a"))]
    return {"files": audio_files}


@app.post("/api/play-audio")
async def play_audio(request: AudioRequest):
    global current_playing, is_playing

    if not SOUND_AVAILABLE:
        return {
            "status": "silent_mode",
            "filename": request.filename,
            "message": f"Silent mode: Would play {request.filename}"
        }

    filename = os.path.basename(request.filename)
    audio_path = os.path.join("audio", filename)

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file {filename} not found")

    try:
        # Stop current playback
        pygame.mixer.music.stop()

        # Load and play new audio
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()

        current_playing = filename
        is_playing = True

        return {
            "status": "playing",
            "filename": filename,
            "message": f"Now playing: {filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error playing: {str(e)}")


@app.post("/api/stop-audio")
async def stop_audio():
    global is_playing
    if SOUND_AVAILABLE:
        pygame.mixer.music.stop()
    is_playing = False
    return {
        "status": "stopped",
        "message": "Аудио остановлено"
    }


@app.get("/api/schedules")
async def get_schedules():
    with open(schedules_path, 'r', encoding="UTF-8") as file:
        data = json.load(file)
    return data


@app.delete("/api/schedules/days/events")
async def remove_event(day: str, time: str):
    with open(schedules_path, 'r', encoding="UTF-8") as file:
        data = json.load(file)

    for schedule in data["schedules"]:
        if schedule["day"] == day:
            schedule["events"] = [e for e in schedule["events"] if e["time"] != time]
            break
    else:
        return {"error": "Day not found"}, 404

    with open(schedules_path, 'w', encoding="UTF-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return {"message": f"Event at {time} on {day} removed"}


@app.post("/api/schedules/days/events")
async def add_event(event: Event):
    day = event.day
    time = event.time
    filepath = event.filepath
    duration = event.duration
    with open(schedules_path, 'r', encoding="UTF-8") as file:
        data = json.load(file)
    if not all([day, time, filepath, duration]):
        return {"error", "not all fields present"}, 400
    for schedule in data["schedules"]:
        if schedule["day"] == day:
            for existing_event in schedule["events"]:
                if existing_event["time"] == time:
                    logger.error(f"event at time {time} already exists")
                    return {"error", f"event at time {time} already exists"}, 409
            schedule["events"].append(
                {"time": time,
                 "filepath": filepath,
                 "duration": duration})
            break
    else:
        logger.error("Day not found")
        return {"error": "Day not found"}, 404
    with open(schedules_path, 'w', encoding="UTF-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    return {"message": f"Event at {time} on {day} added"}