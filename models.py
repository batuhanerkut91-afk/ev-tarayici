from __future__ import annotations
import enum,uuid
from datetime import datetime,timezone
from typing import Optional
from sqlalchemy import String,Float,Integer,Boolean,DateTime,Text,ForeignKey,UniqueConstraint,Index
from sqlalchemy.orm import Mapped,mapped_column,relationship
from .db import Base

def utcnow():return datetime.now(timezone.utc)
def uuid4s():return str(uuid.uuid4())

class SellerRole(str,enum.Enum):
    VERIFIED_OWNER="VERIFIED_OWNER";LIKELY_OWNER="LIKELY_OWNER";AGENT="AGENT";SUSPICIOUS="SUSPICIOUS";UNKNOWN="UNKNOWN"
class CooperationStatus(str,enum.Enum):
    ACCEPT="ACCEPT";REJECT="REJECT";CONDITIONAL="CONDITIONAL";UNKNOWN="UNKNOWN"
class AvailabilityStatus(str,enum.Enum):
    AVAILABLE="AVAILABLE";RESERVED="RESERVED";RENTED="RENTED";SOLD="SOLD";UNKNOWN="UNKNOWN"
class PhotoRightsStatus(str,enum.Enum):
    YES="YES";NO="NO";UNKNOWN="UNKNOWN"
class VisibilityStatus(str,enum.Enum):
    VERIFIED="VERIFIED";FRESH="FRESH";CANDIDATE="CANDIDATE";HIDDEN="HIDDEN"
class MediaStatus(str,enum.Enum):
    CLEAN="CLEAN";WATERMARKED="WATERMARKED";OWNER_ORIGINAL="OWNER_ORIGINAL";PENDING="PENDING";UNKNOWN="UNKNOWN"

class PhysicalProperty(Base):
    __tablename__="physical_properties"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uuid4s)
    canonical_key:Mapped[Optional[str]]=mapped_column(String(180),index=True,nullable=True)
    property_type:Mapped[str]=mapped_column(String(32),default="apartment",index=True)
    city:Mapped[str]=mapped_column(String(120),default="",index=True)
    district:Mapped[str]=mapped_column(String(160),default="",index=True)
    subdistrict:Mapped[str]=mapped_column(String(160),default="",index=True)
    street:Mapped[str]=mapped_column(String(200),default="")
    street_number:Mapped[str]=mapped_column(String(80),default="")
    address:Mapped[str]=mapped_column(String(320),default="")
    cadastral_code:Mapped[Optional[str]]=mapped_column(String(80),nullable=True,index=True)
    area_m2:Mapped[Optional[float]]=mapped_column(Float,nullable=True,index=True)
    rooms:Mapped[Optional[int]]=mapped_column(Integer,nullable=True,index=True)
    bedrooms:Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    floor:Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    floors_total:Mapped[Optional[int]]=mapped_column(Integer,nullable=True)
    latitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    longitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
    offers:Mapped[list["PropertyOffer"]]=relationship(back_populates="physical_property",cascade="all, delete-orphan")

class PropertyOffer(Base):
    __tablename__="property_offers"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uuid4s)
    property_id:Mapped[str]=mapped_column(ForeignKey("physical_properties.id",ondelete="CASCADE"),index=True)
    transaction_type:Mapped[str]=mapped_column(String(24),default="rent",index=True)
    price_usd:Mapped[Optional[float]]=mapped_column(Float,nullable=True,index=True)
    price_gel:Mapped[Optional[float]]=mapped_column(Float,nullable=True)
    availability_status:Mapped[str]=mapped_column(String(24),default=AvailabilityStatus.UNKNOWN.value,index=True)
    visibility_status:Mapped[str]=mapped_column(String(24),default=VisibilityStatus.CANDIDATE.value,index=True)
    manual_availability:Mapped[Optional[str]]=mapped_column(String(24),nullable=True)
    manual_visibility:Mapped[Optional[str]]=mapped_column(String(24),nullable=True)
    verification_note:Mapped[str]=mapped_column(Text,default="")
    verified_at:Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True),nullable=True)
    first_seen_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    last_seen_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
    physical_property:Mapped[PhysicalProperty]=relationship(back_populates="offers")
    listings:Mapped[list["SourceListing"]]=relationship(back_populates="offer",cascade="all, delete-orphan")
    @property
    def effective_availability(self):return self.manual_availability or self.availability_status
    @property
    def effective_visibility(self):return self.manual_visibility or self.visibility_status

class SourceListing(Base):
    __tablename__="source_listings";__table_args__=(UniqueConstraint("source","source_listing_id",name="uq_source_listing"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uuid4s)
    offer_id:Mapped[str]=mapped_column(ForeignKey("property_offers.id",ondelete="CASCADE"),index=True)
    source:Mapped[str]=mapped_column(String(32),index=True);source_listing_id:Mapped[str]=mapped_column(String(64),index=True);source_url:Mapped[str]=mapped_column(Text)
    title:Mapped[str]=mapped_column(Text,default="");description:Mapped[str]=mapped_column(Text,default="")
    seller_role:Mapped[str]=mapped_column(String(32),default=SellerRole.UNKNOWN.value,index=True);seller_role_raw:Mapped[str]=mapped_column(String(80),default="")
    cooperation_status:Mapped[str]=mapped_column(String(24),default=CooperationStatus.UNKNOWN.value,index=True);cooperation_confidence:Mapped[float]=mapped_column(Float,default=0.0)
    refuses_partnership_signal:Mapped[Optional[bool]]=mapped_column(Boolean,nullable=True);photo_rights_status:Mapped[str]=mapped_column(String(24),default=PhotoRightsStatus.UNKNOWN.value,index=True)
    manual_cooperation:Mapped[Optional[str]]=mapped_column(String(24),nullable=True);manual_photo_rights:Mapped[Optional[str]]=mapped_column(String(24),nullable=True);manual_seller_role:Mapped[Optional[str]]=mapped_column(String(32),nullable=True)
    verification_note:Mapped[str]=mapped_column(Text,default="");source_active:Mapped[bool]=mapped_column(Boolean,default=True);raw_excerpt:Mapped[str]=mapped_column(Text,default="")
    first_seen_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow);last_seen_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
    offer:Mapped[PropertyOffer]=relationship(back_populates="listings")
    contacts:Mapped[list["PrivateContact"]]=relationship(back_populates="listing",cascade="all, delete-orphan");media:Mapped[list["MediaAsset"]]=relationship(back_populates="listing",cascade="all, delete-orphan")
    @property
    def effective_seller_role(self):return self.manual_seller_role or self.seller_role
    @property
    def effective_cooperation(self):return self.manual_cooperation or self.cooperation_status
    @property
    def effective_photo_rights(self):return self.manual_photo_rights or self.photo_rights_status

class PrivateContact(Base):
    __tablename__="private_contacts";id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uuid4s);listing_id:Mapped[str]=mapped_column(ForeignKey("source_listings.id",ondelete="CASCADE"),index=True)
    contact_name:Mapped[str]=mapped_column(String(160),default="");phone:Mapped[str]=mapped_column(String(64),default="");has_whatsapp:Mapped[Optional[bool]]=mapped_column(Boolean,nullable=True);has_viber:Mapped[Optional[bool]]=mapped_column(Boolean,nullable=True)
    listing:Mapped[SourceListing]=relationship(back_populates="contacts")
class MediaAsset(Base):
    __tablename__="media_assets";id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uuid4s);listing_id:Mapped[str]=mapped_column(ForeignKey("source_listings.id",ondelete="CASCADE"),index=True)
    url:Mapped[str]=mapped_column(Text);thumb_url:Mapped[Optional[str]]=mapped_column(Text,nullable=True);order_no:Mapped[int]=mapped_column(Integer,default=0);is_main:Mapped[bool]=mapped_column(Boolean,default=False);media_status:Mapped[str]=mapped_column(String(24),default=MediaStatus.UNKNOWN.value);image_hash:Mapped[Optional[str]]=mapped_column(String(128),nullable=True,index=True)
    listing:Mapped[SourceListing]=relationship(back_populates="media")
Index("ix_property_geo",PhysicalProperty.latitude,PhysicalProperty.longitude)
Index("ix_offer_property_transaction",PropertyOffer.property_id,PropertyOffer.transaction_type)
