from __future__ import annotations
import re
from dataclasses import dataclass
from .models import CooperationStatus, PhotoRightsStatus

@dataclass
class Classification:
    cooperation: str
    confidence: float
    photo_rights: str
    reasons: list[str]

def norm(text: str) -> str:
    t=(text or "").lower().replace("აგენტოებთან","აგენტებთან").replace("აგემტებთან","აგენტებთან")
    return re.sub(r"\s+"," ",t).strip()

AGENCY=r"(?:აგენტ\w*|სააგენტო\w*|მაკლერ\w*|ბროკერ\w*|agent\w*|agency|agencies|broker\w*|агент\w*|агентств\w*|брокер\w*|маклер\w*)"
REJECT=[
    rf"{AGENCY}.{{0,60}}(?:არ\s+ვთანამშრომლ|არ\s+დამირეკ|ნუ\s+დამირეკ|არ\s+დამიკავშირდ)",
    rf"(?:არ\s+ვთანამშრომლ|არ\s+ვმუშაობ).{{0,60}}{AGENCY}",
    r"i\s+do\s+not\s+(?:cooperate|work).{0,40}(?:agent|broker|agency)",
    r"(?:no|without)\s+(?:agents?|brokers?)",
    r"не\s+(?:работаю|сотрудничаю).{0,45}(?:агент|брокер|маклер|агентств)",
    r"(?:агент|брокер|маклер).{0,40}не\s+(?:звонить|писать)",
]
ACCEPT=[
    rf"(?:ვთანამშრომლ|ვმუშაობ).{{0,70}}{AGENCY}", rf"{AGENCY}.{{0,70}}(?:ვთანამშრომლ|ვმუშაობ)",
    r"(?:work|cooperate).{0,40}(?:with\s+)?(?:agents?|brokers?|agencies)",
    r"(?:сотрудничаю|работаю).{0,45}(?:агент|брокер|маклер|агентств)",
]
CONDITIONS=[
    r"\b50\s*%",r"\b1\s*%",r"კომისი\w*",r"საკომისიო\w*",r"კლიენტ\w*",r"მხოლოდ",r"სტანდარტულ\w*\s+პირობ",
    r"commission",r"client",r"only\s+if",r"standard\s+terms",r"комисс",r"клиент",r"только\s+если",
]
PHOTO_NO=[
    r"არ\s+დააკოპირ",r"ნუ\s+დააკოპირ",r"არ\s+გაავრცელ",r"ფოტო\w*.{0,40}(?:არ|ნუ).{0,20}დააკოპირ",
    r"do\s+not\s+(?:copy|repost|publish).{0,40}(?:photo|image|listing)",
    r"не\s+(?:копировать|публиковать|размещать).{0,40}(?:фото|объявлен)",
]

def classify(text: str, refuses_partnership_signal: bool|None=None) -> Classification:
    t=norm(text); reasons=[]
    reject=any(re.search(p,t,re.I) for p in REJECT)
    accept=any(re.search(p,t,re.I) for p in ACCEPT)
    cond=any(re.search(p,t,re.I) for p in CONDITIONS)
    if reject:
        cooperation=CooperationStatus.REJECT.value; conf=.99; reasons.append("explicit broker/agent rejection in description")
    elif accept and cond:
        cooperation=CooperationStatus.CONDITIONAL.value; conf=.97; reasons.append("cooperation stated with a condition/commission")
    elif accept:
        cooperation=CooperationStatus.ACCEPT.value; conf=.95; reasons.append("explicit broker/agent cooperation")
    elif refuses_partnership_signal is True:
        cooperation=CooperationStatus.REJECT.value; conf=.80; reasons.append("source refusesPartnership signal")
    else:
        cooperation=CooperationStatus.UNKNOWN.value; conf=.60; reasons.append("no reliable cooperation statement")
    photo_no=any(re.search(p,t,re.I) for p in PHOTO_NO)
    return Classification(cooperation,conf,PhotoRightsStatus.NO.value if photo_no else PhotoRightsStatus.UNKNOWN.value,reasons)
