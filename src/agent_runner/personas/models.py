from __future__ import annotations

from pydantic import BaseModel, Field


class Persona(BaseModel):
    name: str
    display_name: str | None = None
    provider: str = Field(default="stub")
    enabled: bool = True
    prompt: str

    class Config:
        extra = "allow"
