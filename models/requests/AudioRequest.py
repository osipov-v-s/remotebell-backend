from pydantic import BaseModel


class AudioRequest(BaseModel):
    filename: str
