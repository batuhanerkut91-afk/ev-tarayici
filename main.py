from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote
from fastapi import FastAPI,Depends,HTTPException,Header
from fastapi.responses import FileResponse
from sqlalchemy import select,or_
from sqlalchemy.orm import Session,selectinload
from .config import settings
from .db import get_db,init_db
from .models import PhysicalProperty,PropertyOffer,SourceListing
from .schemas import VerificationPatch,LeadRequest,MyHomeExtensionRow
from .services.search import public_search
BASE=Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(app:FastAPI):init_db();yield
app=FastAPI(title="Tiflis Gayrimenkul Property Platform",version="1.2.0",lifespan=lifespan)
def require_admin(x_admin_token:str|None=Header(default=None)):
    if settings.admin_token=="change-me" or x_admin_token!=settings.admin_token:raise HTTPException(401,"Admin token required")
def public_offer(o:PropertyOffer):
    p=o.physical_property;media=[];sources=[]
    for l in o.listings:
        sources.append({"source":l.source,"seller_role":l.effective_seller_role,"cooperation_status":l.effective_cooperation})
        media.extend([m.url for m in sorted(l.media,key=lambda x:x.order_no)])
    return {"id":o.id,"physical_property_id":p.id,"transaction_type":o.transaction_type,"property_type":p.property_type,"city":p.city,"district":p.district,"subdistrict":p.subdistrict,"address":p.address,"price_usd":o.price_usd,"area_m2":p.area_m2,"rooms":p.rooms,"bedrooms":p.bedrooms,"floor":p.floor,"floors_total":p.floors_total,"latitude":p.latitude,"longitude":p.longitude,"availability":o.effective_availability,"media":list(dict.fromkeys(media))[:30],"sources":sources}
@app.get("/")
def home():return FileResponse(BASE/"static"/"public.html")
@app.get("/admin")
def admin():return FileResponse(BASE/"static"/"admin.html")
@app.get("/health")
def health():return {"ok":True,"version":"1.2.0"}
@app.get("/api/public/properties")
def api_public(q:str="",district:str="",max_price:float|None=None,rooms:int|None=None,limit:int=50,db:Session=Depends(get_db)):return [public_offer(x) for x in public_search(db,q,district,max_price,rooms,limit)]
@app.post("/api/public/lead")
def lead(req:LeadRequest,db:Session=Depends(get_db)):
    o=db.get(PropertyOffer,req.property_id)
    if not o:raise HTTPException(404,"Property offer not found")
    p=o.physical_property;msg=req.message or f"Merhaba, {p.district or p.subdistrict} bölgesindeki {p.rooms or ''} odalı ilan hakkında bilgi almak istiyorum. İlan kodu: {o.id[:8]}";number="".join(ch for ch in settings.broker_whatsapp_number if ch.isdigit())
    return {"whatsapp_url":f"https://wa.me/{number}?text={quote(msg)}" if number else None,"message":msg}
@app.get("/api/admin/extension/status",dependencies=[Depends(require_admin)])
def extension_status(db:Session=Depends(get_db)):
    from sqlalchemy import func
    total=db.scalar(select(func.count()).select_from(SourceListing)) or 0
    myhome=db.scalar(select(func.count()).select_from(SourceListing).where(SourceListing.source=="myhome")) or 0
    ss=db.scalar(select(func.count()).select_from(SourceListing).where(SourceListing.source=="ss")) or 0
    return {"ok":True,"source_listings":total,"myhome":myhome,"ss":ss}

@app.post("/api/admin/ingest/myhome",dependencies=[Depends(require_admin)])
def ingest_myhome_extension(row:MyHomeExtensionRow,db:Session=Depends(get_db)):
    from .importers.myhome_benchmark import parse_myhome_row
    from .services.ingest import ingest_listing
    data=parse_myhome_row(row.model_dump())
    if data.get("city")!="Tbilisi":
        return {"imported":False,"reason":"Tiflis dışı"}
    if data.get("seller_role") not in ("VERIFIED_OWNER","LIKELY_OWNER","SUSPICIOUS"):
        return {"imported":False,"reason":"Owner değil","seller_role":data.get("seller_role")}
    if not data.get("source_listing_id"):
        raise HTTPException(400,"listing_id missing")
    physical,offer,listing,created=ingest_listing(db,data)
    return {"imported":True,"created":created,"offer_id":offer.id,"source_listing_id":listing.source_listing_id,"seller_role":listing.effective_seller_role,"cooperation_status":listing.effective_cooperation,"media_count":len(listing.media)}

@app.get("/api/admin/properties",dependencies=[Depends(require_admin)])
def admin_properties(status:str="",source:str="",seller_role:str="",cooperation:str="",q:str="",limit:int=200,db:Session=Depends(get_db)):
    stmt=select(PropertyOffer).join(PropertyOffer.physical_property).options(selectinload(PropertyOffer.physical_property),selectinload(PropertyOffer.listings).selectinload(SourceListing.contacts),selectinload(PropertyOffer.listings).selectinload(SourceListing.media)).order_by(PropertyOffer.last_seen_at.desc())
    if status:stmt=stmt.where(or_(PropertyOffer.manual_visibility==status,(PropertyOffer.manual_visibility.is_(None)&(PropertyOffer.visibility_status==status))))
    if q:stmt=stmt.where(or_(PhysicalProperty.address.ilike(f"%{q}%"),PhysicalProperty.district.ilike(f"%{q}%"),PhysicalProperty.subdistrict.ilike(f"%{q}%")))
    rows=db.scalars(stmt.limit(min(limit,500))).unique().all();out=[]
    for o in rows:
        listings=[]
        for l in o.listings:
            if source and l.source!=source:continue
            if seller_role and l.effective_seller_role!=seller_role:continue
            if cooperation and l.effective_cooperation!=cooperation:continue
            listings.append({"id":l.id,"source":l.source,"source_listing_id":l.source_listing_id,"source_url":l.source_url,"title":l.title,"seller_role":l.effective_seller_role,"cooperation_status":l.effective_cooperation,"photo_rights_status":l.effective_photo_rights,"contacts":[{"name":c.contact_name,"phone":c.phone,"whatsapp":c.has_whatsapp} for c in l.contacts],"media":[m.url for m in sorted(l.media,key=lambda x:x.order_no)][:8]})
        if (source or seller_role or cooperation) and not listings:continue
        x=public_offer(o);x.update({"visibility":o.effective_visibility,"verification_note":o.verification_note,"listings":listings});out.append(x)
    return out
@app.patch("/api/admin/properties/{offer_id}",dependencies=[Depends(require_admin)])
def verify_property(offer_id:str,patch:VerificationPatch,db:Session=Depends(get_db)):
    o=db.get(PropertyOffer,offer_id)
    if not o:raise HTTPException(404,"Property offer not found")
    if patch.availability_status:o.manual_availability=patch.availability_status
    if patch.visibility_status:o.manual_visibility=patch.visibility_status
    if patch.note is not None:o.verification_note=patch.note
    if patch.seller_role or patch.cooperation_status or patch.photo_rights_status:
        for l in o.listings:
            if patch.seller_role:l.manual_seller_role=patch.seller_role
            if patch.cooperation_status:l.manual_cooperation=patch.cooperation_status
            if patch.photo_rights_status:l.manual_photo_rights=patch.photo_rights_status
    from datetime import datetime,timezone
    o.verified_at=datetime.now(timezone.utc);db.commit();return {"ok":True,"id":o.id}
