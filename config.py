from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/tg_property.db")
    admin_token: str = os.getenv("ADMIN_TOKEN", "change-me")
    broker_whatsapp_number: str = os.getenv("BROKER_WHATSAPP_NUMBER", "")
    public_min_visibility: str = os.getenv("PUBLIC_MIN_VISIBILITY", "VERIFIED")

settings = Settings()
