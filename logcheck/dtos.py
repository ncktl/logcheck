from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    path: Path
    language: str
    output: Path
    debug: bool
    alt: bool
    zhenhao: bool
