from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    path: Path
    language: str
    probability: float
    output: Path
    debug: bool
    alt: bool
    zhenhao: bool
