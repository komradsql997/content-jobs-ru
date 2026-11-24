#!/usr/bin/env python3
"""Import only approved Telegram channel posts via the official Telegram Bot API.

A dedicated bot must be an administrator of each approved channel.
Public pages and non-approved channels are never scraped.
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

CONFIG = ROOT / "telegram_sources.json"
STATE = ROOT / "data/telegram_state.json"
ARCHIVE = ROOT / "data/telegram_jobs.json"
MAX_AGE_DAYS = 14
MAX_BATCHES = 8

def read_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def approved_channels(config):
    channels = {}
    for channel in config.get("approved_channels", []):
        username = str(channel.get("username", "")).lstrip("@").strip().lower()
        if re.fullmatch(r"[a-z][a-z0-9_]{4,31}", username) and channel.get("authorized") is True:
            channels[username] = channel
    return channels

def message_text(post):
    return str(post.get("text") or post.get("caption") or "").strip()

def vacancy_title(raw):
    lines = [re.sub(r"^[\s#•*\-–—|📌🔥💼🔎📣✨]+", "", x).strip()
             for x in raw.splitlines() if x.strip()]
    for line in lines[:18]:
        if len(line) > 170:
            continue
        line = re.sub(r"^(?:вакансия|ищем|требуется|открыта позиция|работа)\s*[:—–-]?\s*",
                      "", line, flags=re.I)
        if is_role(line):
            return line[:150].strip(" .:—–-")
    return ""

def job_company(raw):
    match = re.search(r"(?im)^\s*(?:компания|работодатель)\s*[:—–-]\s*([^\n]{2,90})", raw)
    if match:
        return match.group(1).strip(" .")
    return "Работодатель не указан"

def job_location(raw):
    if FOREIGN.search(raw[:1100]):
        return ""
    patterns = [
        r"удал[её]нн\w*\s+(?:из|по)\s+(?:всей\s+)?(?:России|РФ)",
        r"из\s+любого\s+региона\s+(?:России|РФ)",
        r"по\s+всей\s+(?:России|РФ)",
        r"работа\s+в\s+(?:России|РФ)",
    ]
    for pattern in patterns:
        m = re.search(pattern, raw, re.I)
        if m:
            return "Удалённо из России" if re.search(r"удал|из любого", m.group(0), re.I) else "Россия"
    m = RU.search(raw[:1200])
    return m.group(0) if m else ""

def stated_salary(raw):
    # The number must be explicitly connected to compensation, not course/pricing ads.
    for line in raw.splitlines():
        if not re.search(r"зп\b|з\/п|зарплат|оклад|доход|оплата|вознагражден", line, re.I):
            continue
        match = re.search(
            r"(\d[\d\s]{3,10}(?:\s*[-–—]\s*\d[\d\s]{3,10})?\s*(?:₽|руб(?:лей|ля|\.)?))",
            line, re.I)
        if match:
            return match.group(1).strip()
    return ""

def closed(raw):
    return bool(re.search(r"вакансия закрыта|набор закрыт|закрыли вакансию|позиция закрыта", raw[:900], re.I))

def parse_post(post, approved):
    chat = post.get("chat") or {}
    username = str(chat.get("username") or "").lower()
    if username not in approved or chat.get("type") != "channel":
        return None
    message_id = post.get("message_id")
    if not isinstance(message_id, int):
        return None
    raw = message_text(post)
    if len(raw) < 30 or closed(raw):
        return None
    title = vacancy_title(raw)
    if not title:
        return None
    location = job_location(raw)
    if not location:
        return None
    company = job_company(raw)
    url = f"https://t.me/{username}/{message_id}"
    job = make_job(title, company, url, raw[:2100], location, stated_salary(raw))
    if not job:
        return None
    posted_at = dt.datetime.fromtimestamp(post.get("date") or dt.datetime.now(dt.timezone.utc).timestamp(),
                                          tz=dt.timezone.utc)
    if dt.datetime.now(dt.timezone.utc) - posted_at > dt.timedelta(days=MAX_AGE_DAYS):
        return None
    job["id"] = f"telegram-{username}-{message_id}"
    job["channel"] = username
    job["source_kind"] = "telegram"
    job["seen_at"] = posted_at.isoformat(timespec="seconds").replace("+00:00", "Z")
    job["first_seen_at"] = job["seen_at"]
    job["sources"] = [{"name": f"Telegram · @{username}", "url": url}]
    return job

def get_updates(token, offset):
    url = "https://api.telegram.org/bot" + token + "/getUpdates"
    payload = urlencode({
        "offset": offset,
        "timeout": 0,
        "limit": 100,
        "allowed_updates": json.dumps(["channel_post", "edited_channel_post"])
    }).encode()
    with urlopen(Request(url, data=payload, method="POST"), timeout=20) as response:
        result = json.load(response)
    if result.get("ok") is not True:
        raise RuntimeError("Telegram Bot API returned an unsuccessful response")
    return result.get("result", [])

def retain(jobs, approved):
    now = dt.datetime.now(dt.timezone.utc)
    good = []
    for job in jobs:
        if job.get("channel") not in approved:
            continue
        try:
            age = now - dt.datetime.fromisoformat(job["seen_at"].replace("Z", "+00:00"))
        except (ValueError, KeyError, TypeError):
            continue
        if dt.timedelta(0) <= age < dt.timedelta(days=MAX_AGE_DAYS):
            good.append(job)
    return good

def sync_posts(jobs, updates, approved):
    by_post = {job["id"]: job for job in jobs}
    statistics = {"received": 0, "from_approved_channels": 0, "accepted": 0, "removed": 0}
    for update in updates:
        statistics["received"] += 1
        post = update.get("channel_post") or update.get("edited_channel_post")
        if not post:
            continue
        username = str((post.get("chat") or {}).get("username") or "").lower()
        if username not in approved:
            continue
        statistics["from_approved_channels"] += 1
        identity = f"telegram-{username}-{post.get('message_id')}"
        if identity in by_post:
            del by_post[identity]
        job = parse_post(post, approved)
        if job:
            by_post[job["id"]] = job
            statistics["accepted"] += 1
        else:
            statistics["removed"] += 1
    return retain(list(by_post.values()), approved), statistics

def main():
    config = read_json(CONFIG, {"approved_channels": []})
    approved = approved_channels(config)
    state = read_json(STATE, {"offset": 0})
    archived = retain(read_json(ARCHIVE, []), approved)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    stats = {"channels_authorized": len(approved), "received": 0, "accepted": 0, "removed": 0}
    if token and approved:
        offset = int(state.get("offset", 0))
        try:
            for _ in range(MAX_BATCHES):
                updates = get_updates(token, offset)
                if not updates:
                    break
                archived, batch = sync_posts(archived, updates, approved)
                for key in ("received", "accepted", "removed"):
                    stats[key] += batch[key]
                offset = max(offset, max(int(up["update_id"]) for up in updates) + 1)
                if len(updates) < 100:
                    break
        except Exception as error:
            # Never print the API URL: it contains the secret token.
            stats["error"] = type(error).__name__
            print("Telegram fetch failed:", type(error).__name__)
        else:
            state["offset"] = offset
            state["updated_at"] = STAMP
            write_json(STATE, state)
    else:
        print("Telegram disabled: configure a dedicated bot token and authorized channels.")

    write_json(ARCHIVE, archived)
    feed = read_json(FEED, {"jobs": [], "status": {}})
    # Corporate collection has already run; keep the approved Telegram archive separately.
    jobs = merge_jobs(feed.get("jobs", []), archived)
    apply_salary_estimates(jobs)
    jobs.sort(key=lambda j: j.get("first_seen_at", j.get("seen_at", "")), reverse=True)
    statuses = feed.setdefault("status", {})
    for username in approved:
        count = sum(job.get("channel") == username for job in archived)
        statuses[f"Telegram @{username}"] = {"status": "FOUND" if count else "NO_RECENT_APPROVED_POSTS", "saved": count}
    feed["jobs"] = jobs
    feed["total"] = len(jobs)
    write_json(FEED, feed)
    print("TELEGRAM", json.dumps(stats, ensure_ascii=False),
          "stored", len(archived), "total_site_jobs", len(jobs))

if __name__ == "__main__":
    main()
