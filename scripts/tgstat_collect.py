#!/usr/bin/env python3
"""Optional Telegram vacancy ingestion through a third-party licensed feed.

Uses TGStat's documented search/channel-post endpoints, never logs into
Telegram, scrapes Telegram web pages, or needs channel administrator rights.

Not activated without BOTH an API token and confirmed content reuse rights.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from collect import ROOT, FEED, STAMP, RU, FOREIGN, is_role, make_job, merge_jobs, apply_salary_estimates

CONFIG = ROOT / "tgstat_config.json"
ARCHIVE = ROOT / "data/tgstat_jobs.json"
STATE = ROOT / "data/tgstat_state.json"
MAX_AGE_DAYS = 14
MAX_REQUESTS_HARD_CAP = 45

def read_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def get_json(endpoint, token, parameters):
    params = dict(parameters)
    params["token"] = token
    url = f"https://api.tgstat.ru/{endpoint}?" + urlencode(params)
    # Never write the request URL into logs; it contains the private API token.
    with urlopen(Request(url, headers={"Accept": "application/json", "User-Agent": "ContentJobsRU/0.3"}), timeout=18) as response:
        payload = json.load(response)
    if payload.get("status") != "ok":
        raise RuntimeError("TGStat API did not return status=ok")
    return payload.get("response") or {}

def allowed_age(post, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        published = dt.datetime.fromtimestamp(int(post.get("date", 0)), tz=dt.timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return False
    age = now - published
    return dt.timedelta(seconds=-120) <= age < dt.timedelta(days=MAX_AGE_DAYS)

def title_from_text(raw):
    lines = [re.sub(r"^[\s#*•\-—–|💼📌🔎📣🔥✨]+", "", l).strip()
             for l in raw.splitlines() if l.strip()]
    for line in lines[:18]:
        if len(line) > 135:
            continue
        line = re.sub(r"^(?:ищем|вакансия|требуется|открыта позиция)\s*[:—–-]?\s*", "", line, flags=re.I)
        line = line.strip(" «»—–-:,.")
        if len(line) >= 5 and is_role(line):
            return line[:135]
    return ""

def salary_from_text(raw):
    for line in raw.splitlines():
        if len(line) > 240 or not re.search(r"зарплат|оклад|з/п|зп\b|вознагражден|оплата труда", line, re.I):
            continue
        match = re.search(r"\b\d[\d \u00a0]{3,10}(?:\s*[—–-]\s*\d[\d \u00a0]{3,10})?\s*(?:₽|руб(?:лей|ля|\.)?)", line, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).strip()
    return ""

def location_from_text(raw):
    if FOREIGN.search(raw[:1200]):
        return ""
    if re.search(r"удал[её]нн?\w*.{0,30}(?:из|по|для)\s+(?:всей\s+)?(?:России|РФ)", raw, re.I):
        return "Удалённо из России"
    if re.search(r"(?:Россия|РФ).{0,40}удал[её]нн", raw, re.I):
        return "Удалённо из России"
    match = RU.search(raw[:1500])
    return match.group(0) if match else ""

def company_from_text(raw):
    m = re.search(r"(?im)^\s*(?:компания|работодатель|проект)\s*[:—–-]\s*([^\n]{2,90})", raw)
    return m.group(1).strip(" .") if m else "Работодатель не указан"

def safe_post_link(raw):
    link = str(raw or "")
    if not link.startswith("http"):
        link = "https://" + link
    if not re.fullmatch(r"https://t\.me/[a-zA-Z0-9_]{5,32}/\d+(?:\?.*)?", link):
        return ""
    return link.split("?")[0]

def parse_item(post):
    if post.get("is_deleted") in (1, True, "1") or not allowed_age(post):
        return None
    raw = str(post.get("text") or "")
    if len(raw) < 35 or re.search(r"вакансия закрыта|набор закрыт|позиция закрыта", raw[:700], re.I):
        return None
    title = title_from_text(raw)
    location = location_from_text(raw)
    link = safe_post_link(post.get("link"))
    if not title or not location or not link:
        return None
    job = make_job(title, company_from_text(raw), link, raw[:2100], location, salary_from_text(raw))
    if job is None:
        return None
    stamp = dt.datetime.fromtimestamp(int(post["date"]), tz=dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    username = link.split("/")[3]
    job["seen_at"] = stamp
    job["first_seen_at"] = stamp
    job["source_kind"] = "telegram"
    job["channel"] = username
    job["sources"] = [{"name": "Telegram · @" + username, "url": link}]
    return job

def retain(jobs):
    now = dt.datetime.now(dt.timezone.utc)
    result = []
    for j in jobs:
        try:
            when = dt.datetime.fromisoformat(j["seen_at"].replace("Z", "+00:00"))
            if dt.timedelta(seconds=-120) <= now - when < dt.timedelta(days=MAX_AGE_DAYS):
                result.append(j)
        except (KeyError, TypeError, ValueError):
            continue
    return result

def batch_queries(config, state):
    mode = config.get("mode", "search")
    cap = min(MAX_REQUESTS_HARD_CAP, max(0, int(config.get("max_requests_per_run", 5))))
    if mode == "search":
        # Posts search runs across all public indexed channels. This mode requires TGStat Search API.
        terms = [str(q).strip() for q in config.get("search_terms", []) if str(q).strip()]
        return [("posts/search", {"q": q, "peerType": "channel", "limit": 50,
                                  "hideDeleted": 1, "hideForwards": 1, "startDate": str(int(dt.datetime.now(dt.timezone.utc).timestamp()) - 36 * 3600)})
                for q in terms[:cap]]
    if mode == "channels":
        # Channels mode requires paid TGStat Stat API for other people's channels.
        names = [str(u).lstrip("@") for u in config.get("channel_usernames", []) if str(u).strip()]
        if not names or cap == 0:
            return []
        cursor = int(state.get("cursor", 0)) % len(names)
        selected = [names[(cursor + i) % len(names)] for i in range(min(cap, len(names)))]
        state["cursor"] = (cursor + len(selected)) % len(names)
        return [("channels/posts", {"channelId": "@" + name, "limit": 50,
                                    "hideDeleted": 1, "hideForwards": 1, "startTime": str(int(dt.datetime.now(dt.timezone.utc).timestamp()) - 36 * 3600)})
                for name in selected]
    raise ValueError("Unsupported TGStat mode")

def merge_tgstat(older, fresh):
    by_link = {j["url"]: j for j in retain(older) if j.get("url")}
    for j in fresh:
        by_link[j["url"]] = j
    return retain(list(by_link.values()))

def main():
    feed = read_json(FEED, {"jobs": [], "status": {}})
    config = read_json(CONFIG, {})
    archived = retain(read_json(ARCHIVE, []))
    state = read_json(STATE, {"cursor": 0})
    token = os.environ.get("TGSTAT_API_TOKEN", "").strip()
    has_rights = os.environ.get("TGSTAT_RIGHTS_CONFIRMED", "").strip().lower() in ("true", "yes", "1")
    status = {"status": "NOT_CONFIGURED", "mode": config.get("mode", "search"), "saved": len(archived), "queries": 0}
    if not token:
        status["reason"] = "TGSTAT_API_TOKEN is absent"
    elif not has_rights:
        status["status"] = "CONTENT_RIGHTS_NOT_CONFIRMED"
    else:
        fresh = []
        try:
            queries = batch_queries(config, state)
            status["queries"] = len(queries)
            for endpoint, params in queries:
                response = get_json(endpoint, token, params)
                for post in response.get("items") or []:
                    job = parse_item(post)
                    if job:
                        fresh.append(job)
            archived = merge_tgstat(archived, fresh)
            status["status"] = "FOUND" if archived else "NO_MATCHES"
            status["accepted_this_run"] = len(fresh)
            write_json(STATE, state)
        except Exception as e:
            # Never expose raw exception text: URL may contain the API token.
            status["status"] = "PROVIDER_ERROR"
            status["error_type"] = type(e).__name__
    write_json(ARCHIVE, archived)
    site_jobs = merge_jobs(feed.get("jobs", []), archived)
    apply_salary_estimates(site_jobs)
    site_jobs.sort(key=lambda j: j.get("first_seen_at", j.get("seen_at", "")), reverse=True)
    feed["jobs"] = site_jobs
    feed["total"] = len(site_jobs)
    status["saved"] = len(archived)
    feed.setdefault("status", {})["TGStat"] = status
    write_json(FEED, feed)
    print("TGSTAT", json.dumps(status, ensure_ascii=False), "site_total", len(site_jobs))

if __name__ == "__main__":
    main()
