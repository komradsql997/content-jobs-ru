#!/usr/bin/env python3
"""Lightweight reachability audit. Telegram public previews are checked separately; this audit checks employer pages."""
from __future__ import annotations
import concurrent.futures, datetime as dt, json, ssl, socket
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"source_catalog.json"
OUTPUT=ROOT/"reports/source_catalog_health.json"
AGENT="ContentJobsRU/0.2 (+https://github.com/komradsql997/content-jobs-ru)"
def probe(entry):
    row={"id":entry["id"],"name":entry["name"],"url":entry["url"],"kind":entry["type"]}
    if entry["type"]=="telegram_channel":
        row["status"]="PUBLIC_PREVIEW_MONITORED_SEPARATELY"
        return row
    try:
        request=Request(entry["url"],headers={"User-Agent":AGENT,"Accept-Language":"ru-RU,ru;q=0.9"})
        with urlopen(request,timeout=8) as response:
            response.read(4096)
            row["status"]="REACHABLE"
            row["http_status"]=response.status
            row["final_url"]=response.url
    except HTTPError as e:
        row["status"]="BLOCKED" if e.code in (401,403,429) else "HTTP_ERROR"
        row["http_status"]=e.code
    except (TimeoutError, socket.timeout) as e:
        row["status"]="TIMEOUT"
        row["detail"]=str(e)[:120]
    except (ssl.SSLError,URLError) as e:
        row["status"]="NETWORK_OR_TLS_ERROR"
        row["detail"]=str(e)[:120]
    except Exception as e:
        row["status"]="ERROR"
        row["detail"]=str(e)[:120]
    return row

def main():
    entries=json.loads(CATALOG.read_text(encoding="utf-8"))["sources"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=18) as pool:
        rows=list(pool.map(probe,entries))
    counts={}
    for row in rows:
        counts[row["status"]]=counts.get(row["status"],0)+1
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps({"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),"catalog_size":len(rows),"counts":counts,"sources":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SOURCE CATALOG AUDIT",json.dumps(counts,ensure_ascii=False),"TOTAL",len(rows))

if __name__=="__main__":
    main()
