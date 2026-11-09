from __future__ import annotations
import re
from dataclasses import dataclass
from math import radians,sin,cos,sqrt,atan2
from rapidfuzz.fuzz import ratio
@dataclass
class MatchResult:score:float;reasons:list[str];hard_conflict:bool=False
def txt(s):s=(s or "").lower().strip();s=re.sub(r"[^\w\s\-]"," ",s,flags=re.UNICODE);return re.sub(r"\s+"," ",s)
def rel_close(a,b,tol):return False if a is None or b is None else abs(a-b)/max(abs(a),abs(b),1)<=tol
def haversine(a,b,c,d):
    if None in(a,b,c,d):return None
    R=6371000;p1,p2=radians(a),radians(c);dp=radians(c-a);dl=radians(d-b);x=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2;return 2*R*atan2(sqrt(x),sqrt(1-x))
def compare(incoming,prop):
    score=0.;reasons=[];evidence=0.;cad=(incoming.get("cadastral_code") or "").strip();pcad=(prop.cadastral_code or "").strip()
    if cad and pcad:
        if cad==pcad:return MatchResult(1.,["same cadastral code"])
        return MatchResult(0.,["different cadastral codes"],True)
    dist=haversine(incoming.get("latitude"),incoming.get("longitude"),prop.latitude,prop.longitude)
    if dist is not None:
        evidence+=.25
        if dist<=60:score+=.25;reasons.append("coordinates <=60m")
        elif dist<=180:score+=.14;reasons.append("coordinates <=180m")
        elif dist>800:return MatchResult(0,["coordinates conflict"],True)
    ia,pa=incoming.get("area_m2"),prop.area_m2
    if ia is not None and pa is not None:
        evidence+=.20
        if rel_close(ia,pa,.03):score+=.20;reasons.append("area <=3%")
        elif rel_close(ia,pa,.08):score+=.10;reasons.append("area <=8%")
        else:score-=.10;reasons.append("area mismatch")
    ir,pr=incoming.get("rooms"),prop.rooms
    if ir is not None and pr is not None:
        evidence+=.15
        if ir==pr:score+=.15;reasons.append("same rooms")
        else:score-=.12;reasons.append("rooms mismatch")
    if incoming.get("floor") is not None and prop.floor is not None:
        evidence+=.10
        if incoming["floor"]==prop.floor:score+=.10;reasons.append("same floor")
        else:score-=.05
    addr,paddr=txt(incoming.get("address")),txt(prop.address)
    if addr and paddr:
        evidence+=.20;r=ratio(addr,paddr)
        if r>=88:score+=.20;reasons.append("address >=88%")
        elif r>=68:score+=.10;reasons.append("address >=68%")
    hashes=set(incoming.get("image_hashes") or []);existing={m.image_hash for o in prop.offers for l in o.listings for m in l.media if m.image_hash}
    if hashes and existing:
        evidence+=.30
        if hashes&existing:score+=.30;reasons.append("same image fingerprint")
    return MatchResult(max(0,min(1,score/max(evidence,.01))) if evidence else 0,reasons)
