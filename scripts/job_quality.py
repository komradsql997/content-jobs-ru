"""Quality normalization for public vacancy posts and clearly labeled salary guesses."""
from __future__ import annotations
import re

UNKNOWN = "Работодатель не указан"
AD_FOOTER = re.compile(
    r"(?im)^\s*(?:📣\s*)?(?:Разместить ваканси[юи]|Получать больше вакансий"
    r"|Работодром\s+PRO|Разместить рекламу|Предложить вакансию каналу"
    r"|Реклама в канале|Подписаться на канал\s*:)\b.*$"
)
DIVIDER = re.compile(r"^[\s➖▬—–\-_/⚡️📣•·]+$")
PIECE_RATE = re.compile(r"(?:за\s+(?:1\s*)?(?:публикаци[юию]|пост|статью|материал)|за\s+\d+\s*(?:публикаци[и]|поста|статьи))",re.I)
PAY_MONEY = re.compile(r"(?<!\d)(\d(?:[\d \u00a0]{2,10}\d)?)\s*(₽|руб(?:лей|ля|\.)?)",re.I)
COMPANY_LABEL = re.compile(r"(?im)^\s*(?:компания|работодатель|проект|организация|заказчик)\s*[:—–-]\s*(.{2,90})$")
ROLE_ACCU = [
    (r"^UX[\s-]?РЕДАКТОРА$", "UX-редактор"),
    (r"^UX[\s-]?ПИСАТЕЛЯ$", "UX-писатель"),
    (r"^SMM[\s-]?МЕНЕДЖЕРА$", "SMM-менеджер"),
    (r"^РЕДАКТОРА$", "Редактор"),
    (r"^КОПИРАЙТЕРА$", "Копирайтер"),
    (r"^КОНТЕНТ[\s-]?МЕНЕДЖЕРА$", "Контент-менеджер"),
    (r"^КОНТЕНТ[\s-]?МАРКЕТОЛОГА$", "Контент-маркетолог"),
    (r"^ШЕФ[\s-]?РЕДАКТОРА$", "Шеф-редактор"),
]

def clean_post(raw):
    """Remove the channel's promotion/signoff, not the vacancy content."""
    value=str(raw or "").replace("\r\n","\n").replace("\r","\n")
    advert=AD_FOOTER.search(value)
    if advert:value=value[:advert.start()]
    rows=[]
    for line in value.splitlines():
        line=line.strip()
        if not line:rows.append("");continue
        if DIVIDER.fullmatch(line):continue
        if line in ("/", "рекламу", "РЕКЛАМУ"):continue
        rows.append(line)
    return re.sub(r"\n{3,}","\n\n","\n".join(rows)).strip()

def clean_title(raw):
    title=re.sub(r"\s+"," ",str(raw or "")).strip(" \t|•,.;:—–-")
    title=re.sub(r"^.*?\bищ(?:ет|ут)\s+", "", title, flags=re.I)
    title=re.sub(r"^(?:вакансия|должность|позиция|роль)\s*[:—–-]?\s*","",title,flags=re.I)
    title=title.split("|")[0].strip(" ,.;:—–-")
    for pattern,normalized in ROLE_ACCU:
        if re.fullmatch(pattern,title,re.I):return normalized
    # All-caps text from a job channel isn't a proper job title.
    if title.isupper() and len(title)>3:
        return title[:1].upper()+title[1:].lower()
    return title

def employer(raw):
    text=clean_post(raw)
    match=COMPANY_LABEL.search(text)
    if match:return match.group(1).strip(" .,:;—–")
    # "Работодатель" and the name may be on separate lines.
    match=re.search(r"(?im)^\s*(?:работодатель|название платформы|название компании)\s*:\s*\n\s*([^\n]{3,70})",text)
    if match:return match.group(1).strip(" .,:;—–")
    match=re.search(r"(?im)^\s*Название платформы:\s*([^\n]{3,70})",text)
    if match:return match.group(1).strip(" .,:;—–")
    # "Команда образовательной платформы Нетология ищет РЕДАКТОРА."
    match=re.search(r"(?im)^(?:.{0,95}?\b(?:команда|компания|платформа|агентство|студия)\b.{0,85}?\s)?([А-ЯЁ][а-яёA-Za-z0-9.\-]{2,40})\s+ищ(?:ет|ут)\s+[\wА-Яа-яёЁ-]{4,}",text)
    if match:
        name=match.group(1)
        if name.lower() not in ("команда","компания","ищет","ищут","редактора","копирайтера"):
            return name
    return UNKNOWN

def stated_pay(raw):
    """Only amounts explicitly described as compensation, including piece rate."""
    text=clean_post(raw)
    lines=text.splitlines()
    for idx,line in enumerate(lines):
        payment_context=bool(re.search(r"\b(?:заработн|зарплат|оклад|вознаграждени|оплата труда|з/п|зп\b|уровень заработной платы|ставка)\b",line,re.I))
        by_piece=bool(PIECE_RATE.search(line))
        if not (payment_context or by_piece):continue
        possible=line+" "+(" ".join(lines[idx+1:idx+3]) if payment_context else "")
        match=PAY_MONEY.search(possible)
        if not match:continue
        amount=int(re.sub(r"\D","",match.group(1)))
        if by_piece or PIECE_RATE.search(possible):
            if 300<=amount<=250000:
                unit="за публикацию" if re.search(r"публикаци",possible,re.I) else ("за статью" if "стать" in possible.lower() else "за пост")
                return f"{amount:,} ₽ {unit}".replace(","," ")
        elif 20000<=amount<=1000000:
            clean=match.group(0).strip()
            return re.sub(r"\s+"," ",clean)
    return ""

# Approximate monthly ranges for full-time vacancies, not salary predictions for a
# particular employer. Broad heuristics based on 2026 Russian salary surveys:
# t-j.ru/zarplata-text-2026/ ; d-pub.ru/research/zarplaty-digital-2026
MARKET_THOUSANDS={
    "Редактура":(85,145),
    "UX-тексты":(140,225),
    "Копирайтинг":(60,105),
    "Контент-маркетинг":(95,160),
    "SMM":(65,120),
    "Технические тексты":(105,170),
    "Руководство":(155,255),
}
LEVEL_SHIFT={"intern":(-35,-45),"junior":(-25,-35),"middle":(0,0),"senior":(35,65),"lead":(65,110)}
PART_TIME = re.compile(r"\b(?:парт[\s-]?тайм|part[\s-]?time|фриланс|подработк|частичн(?:ая|ую|ой)\s+занятост|разов(?:ый|ая)\s+заказ|проектн(?:ая|ую)\s+работа|по\s+публикаци|за\s+статью|за\s+пост|почасов|часовая ставка)\b",re.I)

def market_guess(job):
    """Return transparent, coarse market guess, not employer salary."""
    if job.get("salary"):return ""
    text=" ".join((str(job.get("title") or ""),str(job.get("description") or "")[:600]))
    if PART_TIME.search(text):return ""
    lo,hi=MARKET_THOUSANDS.get(job.get("category"),(75,140))
    shift=LEVEL_SHIFT.get(job.get("level"),(0,0))
    lo=max(25,int(round((lo+shift[0])/5))*5)
    hi=max(lo+20,int(round((hi+shift[1])/5))*5)
    return f"{lo}–{hi} тыс. ₽/мес"
