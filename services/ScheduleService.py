import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pygame.mixer

SCHEDULES_PATH = Path("schedules/schedules.json")
AUDIO_DIR = Path("audio")
CHECK_INTERVAL_SECONDS = 60


try:
    pygame.mixer.init()
    SOUND_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("Sound initialized successfully")
except Exception as e:
    SOUND_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Sound not available (running in silent mode): {e}")

class ScheduleService:
    def __init__(self, schedule_path: Path, audio_dir: Path):
        self.schedules_path = schedule_path
        self.audio_dir = audio_dir
        self.current_playing: Optional[str] = None

    async def run(self):
        while True:
            await self.check_current_time()
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    async def check_current_time(self):
        now = datetime.now()
        current_day = now.strftime("%A").lower()
        current_time = now.strftime("%H:%M")

        events = self._get_events_for_day(current_day)
        event = self._find_event_at_time(events, current_time)
        if event:
            await self._play_event(event)

    def _get_events_for_day(self, day: str):
        if not self.schedules_path.exists():
            return []
        with open(self.schedules_path, 'r', encoding="UTF-8") as file:
            data = json.load(file)
        for schedule in data.get("schedules", []):
            if schedule.get("day") == day:
                return schedule.get("events", [])
        return []

    def _find_event_at_time(self, events, time):
        for event in events:
            if event.get('time') == time:
                return event
        return None

    async def _play_event(self, event):
        if not SOUND_AVAILABLE:
            logger.info(f"Silent mode: Would play {event.get('filepath')} at {event['time']}")
            return
            
        filename = Path(event["filepath"]).name
        audio_path = self.audio_dir / filename
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return
        if self.current_playing == filename:
            return
        pygame.mixer.music.load(str(audio_path))
        pygame.mixer.music.play()
        self.current_playing = filename
        logger.info(f"Playing: {filename} at {event['time']}")
        if duration := event.get("duration"):
            await asyncio.sleep(duration)
            pygame.mixer.music.stop()
            self.current_playing = None