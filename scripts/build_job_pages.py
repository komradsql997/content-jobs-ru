#!/usr/bin/env python3
"""Build shareable static vacancy pages for GitHub Pages (no backend)."""
from __future__ import annotations
import datetime as dt
import hashlib
import html
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
FEED=SITE/"jobs.json"
HISTORY=SITE/"job-history.json"
OUTPUT=SITE/"v"
DOMAIN="https://komradsql997.github.io/content-jobs-ru/"
KEEP_DAYS=45

def stable_id(job):
    url=str(job.get("url",""))
    # Use source URL, not job title, so two different openings cannot share an ID.
    if str(job.get("source_kind","")).startswith("telegram") and job.get("channel"):
        parts=re.search(r"/([A-Za-z0-9_]+)/(\d+)$",url)
        if parts:return "telegram-"+parts.group(1)+"-"+parts.group(2)
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]

def iso_date(value):
    try:
        d=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except (TypeError,ValueError):
        return None

def safe_json(data):
    # Prevent closing the inline JSON <script> element with untrusted post content.
    return json.dumps(data,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")

def render_page(job,active):
    ident=stable_id(job)
    title=str(job.get("title") or "Вакансия")
    company=str(job.get("company") or "Работодатель не указан")
    page_title=title+" — "+company+" | Главред проверил вакансию"
    excerpt=re.sub(r"\s+"," ",str(job.get("description") or ""))[:170] or "Подробности вакансии и ссылка на первоисточник."
    uri=DOMAIN+"v/"+ident+".html"
    esc=lambda v:html.escape(str(v),quote=True)
    payload=safe_json({"job":job,"active":bool(active)})
    robots="index,follow" if active else "noindex,follow"
    return f"""<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(page_title)}</title>
<meta name="description" content="{esc(excerpt)}"><meta name="robots" content="{robots}">
<link rel="canonical" href="{esc(uri)}">
<meta property="og:type" content="article"><meta property="og:title" content="{esc(title+' — '+company)}">
<meta property="og:description" content="{esc(excerpt)}"><meta property="og:url" content="{esc(uri)}">
<meta property="og:image" content="{DOMAIN}brand.jpg">
<meta name="twitter:card" content="summary">
<link rel="icon" href="../favicon.svg?v=4" type="image/svg+xml">
<link rel="stylesheet" href="../styles.css?v=8">
<script defer src="../job-text.js?v=8"></script>
<script defer src="../job-detail.js?v=8"></script>
</head><body>
<header><div class="wrap head"><a href="../" class="logo"><img src="../brand.jpg?v=3" alt="" width="42" height="42"><span>Главред проверил вакансию</span></a><span class="pill">Бета-версия</span></div></header>
<main class="wrap"><div class="job-page"><a class="job-breadcrumb" href="../">← К списку вакансий</a><div id="vacancy-content"></div></div></main>
<footer><div class="wrap foot"><a class="footer-link" href="https://t.me/leadofcringejobs" target="_blank" rel="noopener noreferrer">Главред проверил вакансию</a><span>Работа в контенте · Россия · 2026</span></div></footer>
<script id="vacancy-data" type="application/json">{payload}</script>
</body></html>
"""

def build(site=SITE):
    feed=json.loads((site/"jobs.json").read_text(encoding="utf-8"))
    history_path=site/"job-history.json"
    history=json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {"items":{}}
    existing=history.get("items",{})
    now=dt.datetime.now(dt.timezone.utc)
    stamp=now.isoformat(timespec="seconds").replace("+00:00","Z")
    active=set()
    for job in feed.get("jobs",[]):
        if not isinstance(job,dict) or not job.get("url"):
            continue
        ident=stable_id(job)
        job["id"]=ident
        active.add(ident)
        existing[ident]={"job":job,"last_seen_at":stamp}
    cutoff=dt.timedelta(days=KEEP_DAYS)
    for ident,record in list(existing.items()):
        dt_value=iso_date(record.get("last_seen_at"))
        if not dt_value or now-dt_value>cutoff:
            del existing[ident]
    history={"updated_at":stamp,"items":existing}
    history_path.write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    folder=site/"v";folder.mkdir(parents=True,exist_ok=True)
    written=set()
    for ident,record in existing.items():
        if not re.fullmatch(r"[a-zA-Z0-9_-]{8,90}",ident):
            continue
        target=folder/(ident+".html")
        target.write_text(render_page(record["job"],ident in active),encoding="utf-8")
        written.add(target.name)
    for file in folder.glob("*.html"):
        if file.name not in written:file.unlink()
    print("JOB_PAGES",len(written),"active",len(active),"archived",len(written)-len(active))
    return len(written),len(active)

if __name__=="__main__":
    build()
