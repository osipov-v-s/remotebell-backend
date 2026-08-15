from pydantic import BaseModel


class Event(BaseModel):
    day: str
    time: str
    duration: int = 30
    filepath: str
