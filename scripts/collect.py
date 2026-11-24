#!/usr/bin/env python3
"""Russian content-jobs feed: best-effort corporate-site collectors, no paywalled APIs."""
from __future__ import annotations
import concurrent.futures, datetime as dt, difflib, hashlib, json, re, ssl
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "sources.json"
FEED = ROOT / "site/jobs.json"
REPORT = ROOT / "reports/source_diagnostics.json"
UTC_NOW = dt.datetime.now(dt.timezone.utc)
STAMP = UTC_NOW.isoformat(timespec="seconds").replace("+00:00", "Z")
TITLE = re.compile(r"редактор|главред|шеф.редактор|копирайт|контент[ -]?(?:менеджер|маркетолог|редактор|продюсер|стратег|лид|специалист|директор)|ux[ -]?(?:писател|редактор|райтер)|техническ.{0,12}писател|техпис|журналист|корректор|автор (?:статей|текстов)|smm[ -]?(?:редактор|менеджер)", re.I)
BAD_TITLE = re.compile(r"видеоредактор|видео.редактор|монтажер|монтажёр|модератор|фотограф|дизайнер|аналитик|разработчик", re.I)
FOREIGN = re.compile(r"\b(?:usa|us only|uk only|united kingdom|worldwide|global remote|europe only|eu only)\b|германи[яию]|польш[аеу]|казахстан|беларус[ьи]|армени[яию]|грузи[яию]|кипр", re.I)
RU = re.compile(r"\b(?:росси[ияию]|рф|москв[аеуы]|мск|спб|казан[ьи]|самар[аеу]|новосибирск|екатеринбург|краснодар)\b|санкт.петербург|нижн.{0,8}новгород|\bтк\s*рф\b|\bиз рф\b|\bпо рф\b", re.I)
SALARY = re.compile(r"(?:\d[\d\s]{3,12})(?:\s*[-–]\s*\d[\d\s]{3,12})?\s*(?:₽|руб(?:лей|ля|\.)?|р\./мес)", re.I)
HEADER = {"User-Agent": "Mozilla/5.0 (compatible; ContentJobsRU/0.1; +https://github.com/komradsql997/content-jobs-ru)", "Accept-Language": "ru-RU,ru;q=0.9"}
MAX_DETAILS = 16
MAX_AGE_DAYS = 7

def plain(value, limit=2500):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]

def canonical(url):
    p = urlparse(url)
    q = [(k,v) for k,v in parse_qsl(p.query) if k not in ("utm_source","utm_medium","utm_campaign","utm_content","utm_term","from","ref")]
    return urlunparse((p.scheme.lower(),p.netloc.lower(),p.path.rstrip("/") or "/", "", urlencode(q), ""))

def is_role(text):
    return bool(TITLE.search(text or "")) and not bool(BAD_TITLE.search(text or ""))

def category(title):
    t = title.lower()
    if "ux" in t or "интерфейс" in t: return "UX-тексты"
    if "главред" in t or "шеф" in t or "руковод" in t or "лид" in t: return "Руководство"
    if "техпис" in t or "техническ" in t: return "Технические тексты"
    if "копирайт" in t: return "Копирайтинг"
    if "маркет" in t or "smm" in t: return "Контент-маркетинг"
    return "Редактура"

def score(job):
    desc = job.get("description", "")
    points = 0
    points += 25 if job.get("salary") else 0
    points += 20 if re.search(r"задач|обязанност|предстоит|заниматься|делать", desc, re.I) else 0
    points += 20 if re.search(r"требован|ожидаем|опыт|навык|умеешь", desc, re.I) else 0
    points += 15 if job.get("location") else 0
    points += 10 if job.get("company") else 0
    points += 10 if job.get("url") else 0
    return points

def http_get(url):
    req = Request(url, headers=HEADER)
    with urlopen(req, timeout=14) as r:
        if r.status >= 400: raise RuntimeError("HTTP " + str(r.status))
        html = r.read(1500000).decode(r.headers.get_content_charset() or "utf-8", "replace")
    return BeautifulSoup(html, "html.parser")

def jobs_schema(soup):
    found=[]
    for tag in soup.select('script[type="application/ld+json"]'):
        try: obj=json.loads(tag.string or tag.get_text())
        except (ValueError,TypeError): continue
        def walk(x):
            if isinstance(x,list):
                for z in x: yield from walk(z)
            elif isinstance(x,dict):
                t=x.get("@type",[])
                if isinstance(t,str): t=[t]
                if "JobPosting" in t: yield x
                for z in x.values():
                    if isinstance(z,(list,dict)): yield from walk(z)
        found.extend(walk(obj))
    return found

def structured_job(obj,base,company):
    title=plain(obj.get("title"),170)
    desc=plain(BeautifulSoup(str(obj.get("description","")), "html.parser").get_text(" "),2100)
    loc=obj.get("jobLocation",[])
    if isinstance(loc,dict): loc=[loc]
    location=" ".join(plain((x.get("address") or {}).get("addressLocality",""),100) for x in loc if isinstance(x,dict))
    if not location and obj.get("jobLocationType")=="TELECOMMUTE": location="Удалённо"
    salary=plain(obj.get("baseSalary",""),130)
    url=obj.get("url") or base
    return make_job(title, company, urljoin(base,str(url)), desc, location, salary)

def make_job(title,company,url,description="",location="",salary=""):
    title=plain(title,180); description=plain(description,2100); location=plain(location,140)
    if not is_role(title) or FOREIGN.search(title+" "+location): return None
    if not location:
        m=RU.search(description)
        if m: location=m.group(0)
    if not location or (not RU.search(location) and location.lower() not in ("удалённо из россии","удаленно из россии")):
        return None
    if FOREIGN.search(location): return None
    if not salary:
        m=SALARY.search(description)
        if m: salary=m.group(0)
    u=canonical(url)
    job={"title":title,"company":company,"url":u,"sources":[{"name":company,"url":u}],"description":description,"location":location,"salary":salary,"category":category(title),"seen_at":STAMP}
    job["score"]=score(job)
    job["id"]=hashlib.sha256((company.lower()+"|"+title.lower()).encode()).hexdigest()[:16]
    return job

def parse_detail(url,company):
    soup=http_get(url)
    for tag in jobs_schema(soup):
        result=structured_job(tag,url,company)
        if result: return result
    heading=soup.select_one("h1")
    title=plain(heading.get_text(" ") if heading else "",180)
    excerpt=plain((soup.select_one("main") or soup.body or soup).get_text(" "),2200)
    if re.search(r"вакансия в архиве|вакансия закрыта|позиция закрыта|не актуальна",excerpt,re.I): return None
    return make_job(title,company,url,excerpt)

def collect_company(source):
    name=source["name"]; rx=re.compile(source["path_regex"])
    stats={"status":"OK","listing_pages":0,"links":0,"candidate_links":0,"detail_checked":0,"saved":0}
    found=[]; candidates={}
    for listing in [source["url"]]+source.get("extra_urls",[]):
        try:
            soup=http_get(listing); stats["listing_pages"]+=1
            for obj in jobs_schema(soup):
                item=structured_job(obj,listing,name)
                if item: found.append(item)
            for a in soup.find_all("a",href=True):
                href=urljoin(listing,a.get("href",""))
                if urlparse(href).netloc!=urlparse(listing).netloc: continue
                stats["links"]+=1
                if rx.search(urlparse(href).path):
                    stats["candidate_links"]+=1
                    label=plain(a.get_text(" "),190)
                    parent=plain(a.parent.get_text(" ") if a.parent else "",250)
                    candidates[canonical(href)]=(label,parent)
        except Exception as e:
            stats["status"]="FETCH_ERROR";stats["error"]=str(e)[:200]
    for url,(label,parent) in list(candidates.items())[:MAX_DETAILS]:
        try:
            item=parse_detail(url,name);stats["detail_checked"]+=1
            if item: found.append(item)
        except Exception as e:
            stats.setdefault("detail_errors",[]).append(str(e)[:130])
    unique={j["url"]:j for j in found}
    result=list(unique.values());stats["saved"]=len(result)
    if stats["status"]!="FETCH_ERROR":
        stats["status"]="FOUND" if result else ("NO_MATCHES_IN_CHECKED_PAGES" if stats["candidate_links"] or stats["listing_pages"] else "NO_LISTING_DATA")
    return name,result,stats

def merge_jobs(existing,incoming):
    all_jobs=[]
    for job in existing+incoming:
        matched=None
        for saved in all_jobs:
            same_link=job["url"]==saved["url"]
            same_name=(job["company"].casefold()==saved["company"].casefold() and difflib.SequenceMatcher(None,job["title"].casefold(),saved["title"].casefold()).ratio()>=.96)
            if same_link or same_name:matched=saved;break
        if matched:
            links={s["url"]:s for s in matched.get("sources",[])+job.get("sources",[])}
            matched["sources"]=list(links.values())
            if len(job.get("description",""))>len(matched.get("description","")):matched["description"]=job["description"]
            if job.get("salary") and not matched.get("salary"):matched["salary"]=job["salary"]
            matched["score"]=score(matched)
        else:all_jobs.append(dict(job))
    return all_jobs

def main():
    sources=json.loads(SOURCE_FILE.read_text(encoding="utf-8"))["companies"]
    status={};new=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for name,jobs,details in pool.map(collect_company,sources):
            status[name]=details;new+=jobs
            print(name,details["status"],"cards",details["candidate_links"],"checked",details["detail_checked"],"saved",details["saved"])
    prev=json.loads(FEED.read_text(encoding="utf-8")) if FEED.exists() else {}
    old=[]
    for job in prev.get("jobs",[]):
        try: age=(UTC_NOW-dt.datetime.fromisoformat(job["seen_at"].replace("Z","+00:00"))).days
        except (ValueError,KeyError,TypeError): continue
        if age<MAX_AGE_DAYS:old.append(job)
    fresh_urls={j["url"] for j in new}
    old=[j for j in old if j.get("url") not in fresh_urls]
    jobs=merge_jobs(new,old)
    jobs.sort(key=lambda x:x.get("seen_at",""),reverse=True)
    result={"updated_at":STAMP,"total":len(jobs),"status":status,"jobs":jobs}
    FEED.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps({"at":STAMP,"sources":status,"found_today":len(new),"total":len(jobs)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("TOTAL",len(jobs),"NEW",len(new),"REPORT",REPORT.relative_to(ROOT))

if __name__=="__main__":main()
