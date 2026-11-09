from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

class VerificationPatch(BaseModel):
    seller_role: Optional[str]=None
    cooperation_status: Optional[str]=None
    photo_rights_status: Optional[str]=None
    availability_status: Optional[str]=None
    visibility_status: Optional[str]=None
    note: Optional[str]=None

class LeadRequest(BaseModel):
    property_id: str
    name: str = ""
    message: str = ""


class MyHomeExtensionRow(BaseModel):
    source: str = "myhome"
    listing_id: str
    url: str
    title: str = ""
    body_excerpt: str = ""
    seller_role: str = "UNKNOWN"
    full_media_urls: list[str] = Field(default_factory=list)
    contacts: list[dict] = Field(default_factory=list)
