#!/usr/bin/env python3
"""Best-effort public Telegram channel preview reader.

Only publicly viewable t.me/s pages; no account login, API key, proxy or bypass.
Use short summaries and links to original posts; respect robots and rate limits.
"""
from __future__ import annotations
import concurrent.futures, datetime as dt, json, re, time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from collect import ROOT, FEED, STAMP, is_role, FOREIGN, RU, make_job, merge_jobs, apply_salary_estimates

CATALOG=ROOT/"source_catalog.json"
ARCHIVE=ROOT/"data/telegram_public_jobs.json"
REPORT=ROOT/"reports/telegram_public_diagnostics.json"
MAX_AGE=14
MAX_CHANNELS=45
HEADERS={"User-Agent":"ContentJobsRU/0.3 (public vacancy index; +https://github.com/komradsql997/content-jobs-ru)","Accept-Language":"ru-RU,ru;q=0.9"}
BLACKLIST=re.compile(r"ваканси[яи]\s+закрыт|набор\s+закрыт|не\s+актуальн|пост\s+удалён",re.I)
LOCATION=re.compile(r"удал[её]нн?.{0,50}(?:по\s+(?:всей\s+)?России|из\s+(?:России|РФ)|в\s+(?:России|РФ))|из\s+любого\s+региона\s+(?:РФ|России)",re.I)
PAY=re.compile(r"(\d[\d \u00a0]{3,10}(?:\s*[–—-]\s*\d[\d \u00a0]{3,10})?\s*(?:₽|руб(?:лей|ля|\.)?))",re.I)
START=re.compile(r"^(?:вакансия|ищем|требуется|открыта позиция|ищу)\s*[—–:\-]?\s*",re.I)
NOISE=re.compile(r"^[\s#*•\-—–|💼📌🔎📣🔥✨✅]+")
COMMON=["редактор","главред","шеф-редактор","копирайтер","контент","smm","ux-писатель","ux-редактор","техпис","журналист"]

def load(path,default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError): return default

def save(path,value):
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def text_lines(raw):
    lines=[NOISE.sub("",line).strip(" «».,:;—-") for line in raw.splitlines()]
    return [x for x in lines if x and len(x)>3]

def job_title(raw):
    lines=text_lines(raw)
    if not lines:return ""
    beginning=" ".join(lines[:2]).lower()
    if re.search(r"^резюме\b|^ищу\s+работу|^подборк[аи]\s+ваканс|^ищет\s+работу|^анкета\s+кандидата",beginning,re.I):
        return ""
    # Posts about an entirely different role must not be classified by their duties.
    if re.search(r"\b(?:видеограф|видеооператор|дизайнер|монтаж[её]р)\b",lines[0],re.I) and not is_role(lines[0]):
        return ""
    for line in lines[:6]:
        line=START.sub("",line)
        line=re.sub(r"^(?:должность|позиция|роль)\s*[:—–-]?\s*", "", line, flags=re.I)
        line=re.sub(r"^.*?\bищет\s+(?=[^\n]{0,40}(?:редактор|копирайт|smm|контент))","",line,flags=re.I)
        if re.match(r"^(?:участвовать|помогать|поддерживать|создавать|разрабатывать|писать|подбирать|анализировать|следить|мониторить|проводить|публиковать)\b",line,re.I):
            continue
        if 5<=len(line)<=105 and is_role(line):
            return line.strip(" !,.;")
        for piece in re.split(r"\s*[|•]\s*",line)[:3]:
            if 5<=len(piece)<=90 and is_role(piece):return piece
    return ""

def company(raw):
    m=re.search(r"(?im)^\s*(?:компания|работодатель|проект)\s*[:—–-]\s*(.{2,90})$",raw)
    return m.group(1).strip() if m else "Работодатель не указан"

def location(raw):
    if FOREIGN.search(raw[:1500]):return ""
    m=LOCATION.search(raw[:1600])
    if m:return "Удалённо из России"
    m=RU.search(raw[:1600])
    if m:
        return "Россия" if "ТК" in m.group(0).upper() else m.group(0)
    return ""

def salary(raw):
    for line in raw.splitlines():
        if len(line)>260:continue
        if not re.search(r"зарплат|зп\b|з/п|оклад|доход|оплата труда|вознаграждени",line,re.I):continue
        m=PAY.search(line)
        if m:return re.sub(r"\s+"," ",m.group(1)).strip()
    return ""

def get_date(block):
    t=block.select_one(".tgme_widget_message_date time[datetime]")
    if t:
        try: return dt.datetime.fromisoformat(t.get("datetime").replace("Z","+00:00"))
        except ValueError:pass
    return None

def parse_preview(html, channel, now=None):
    soup=BeautifulSoup(html,"html.parser")
    now=now or dt.datetime.now(dt.timezone.utc)
    results=[]; seen=set(); scanned=0; relevant=0
    for block in soup.select(".tgme_widget_message[data-post]"):
        post=block.get("data-post","")
        if not re.fullmatch(re.escape(channel)+r"/\d+",post,re.I):continue
        scanned+=1
        date=get_date(block)
        if not date or not dt.timedelta(0)<=now-date<dt.timedelta(days=MAX_AGE):continue
        content=block.select_one(".tgme_widget_message_text")
        if not content:continue
        raw=content.get_text("\n",strip=True)
        if len(raw)<30 or BLACKLIST.search(raw[:600]):continue
        title=job_title(raw)
        if not title:continue
        relevant+=1
        region=location(raw)
        if not region:continue
        url="https://t.me/"+post
        j=make_job(title,company(raw),url,raw[:5800],region,salary(raw))
        if not j:continue
        j["id"]="telegram-"+post.replace("/","-")
        j["channel"]=channel
        j["source_kind"]="telegram_public"
        j["extraction_version"]=2
        j["seen_at"]=date.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
        j["first_seen_at"]=j["seen_at"]
        j["sources"]=[{"name":"Telegram · @"+channel,"url":url}]
        if url not in seen:results.append(j);seen.add(url)
    return results,{"posts_scanned":scanned,"role_matches":relevant,"saved":len(results)}

def channels():
    rows=load(CATALOG,{ }).get("sources",[])
    result=[];used=set()
    for item in rows:
        if item.get("type")!="telegram_channel":continue
        username=str(item.get("name","")).lstrip("@").strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}",username):continue
        if username.lower() not in used:
            result.append(username);used.add(username.lower())
    return result[:MAX_CHANNELS]

def robots_allowed(url):
    parser=RobotFileParser()
    parser.set_url("https://t.me/robots.txt")
    try:
        parser.read()
        return parser.can_fetch(HEADERS["User-Agent"],url)
    except Exception:
        # Do not harvest if robots policy cannot be confirmed.
        return False

def fetch(channel):
    url="https://t.me/s/"+channel
    if not robots_allowed(url):
        return channel,[],{"status":"ROBOTS_UNAVAILABLE_OR_DISALLOWED","saved":0}
    try:
        req=Request(url,headers=HEADERS)
        with urlopen(req,timeout=13) as response:
            if response.status!=200:raise RuntimeError("HTTP "+str(response.status))
            html=response.read(1600000).decode("utf-8","replace")
        jobs,diag=parse_preview(html,channel)
        diag["status"]="FOUND" if jobs else "NO_MATCHES_IN_RECENT_PUBLIC_POSTS"
        return channel,jobs,diag
    except Exception as ex:
        return channel,[],{"status":"ERROR","error_type":type(ex).__name__,"saved":0}

def retain(jobs):
    now=dt.datetime.now(dt.timezone.utc)
    out=[]
    for j in jobs:
        try:
            # Old parser output included resumes and action sentences as job titles.
            # Refresh from the public source rather than retaining low-quality cached cards.
            if int(j.get("extraction_version",0))<2:continue
            moment=dt.datetime.fromisoformat(j["seen_at"].replace("Z","+00:00"))
            if dt.timedelta(0)<=now-moment<dt.timedelta(days=MAX_AGE):out.append(j)
        except (TypeError,ValueError,KeyError):pass
    return out

def run():
    selected=channels()
    prev=load(ARCHIVE,[])
    by_url={j["url"]:j for j in retain(prev)}
    statuses={};new=0;success=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for name,jobs,diag in pool.map(fetch,selected):
            statuses[name]=diag
            if diag["status"] not in ("ERROR","ROBOTS_UNAVAILABLE_OR_DISALLOWED"):
                success+=1
            for j in jobs:
                by_url[j["url"]]=j
                new+=1
            print("TELEGRAM",name,diag["status"],"scanned",diag.get("posts_scanned",0),"saved",diag.get("saved",0))
    archive=retain(list(by_url.values()))
    save(ARCHIVE,archive)
    feed=load(FEED,{"jobs":[],"status":{}})
    # First corporate collection runs, then public Telegram updates.
    all_jobs=merge_jobs(feed.get("jobs",[]),archive)
    apply_salary_estimates(all_jobs)
    all_jobs.sort(key=lambda j:j.get("first_seen_at",j.get("seen_at","")),reverse=True)
    feed["jobs"]=all_jobs
    feed["total"]=len(all_jobs)
    for name,status in statuses.items():
        feed.setdefault("status",{})["Telegram @"+name]=status
    save(FEED,feed)
    save(REPORT,{"updated_at":STAMP,"channels_configured":len(selected),"channels_checked":success,"new_jobs":new,"active_archive":len(archive),"status":statuses})
    print("TELEGRAM_SUMMARY",json.dumps({"configured":len(selected),"checked":success,"new":new,"active":len(archive),"site_total":len(all_jobs)},ensure_ascii=False))

if __name__=="__main__":run()
