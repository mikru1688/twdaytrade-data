#!/usr/bin/env python3
"""Collect daily after-hours open data (raw JSON) for TWDayTrade.

Only public open-data endpoints. Each source is saved as
data/raw/<source>/<YYYY-MM-DD>.json (data date when available, else Taipei fetch date).
A file is written only when its content differs from the latest saved file of that source.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
UA = "twdaytrade-data-collector/1.0 (+https://github.com/mikru1688/twdaytrade-data)"
GAP_SECONDS = 5

SOURCES = {
    # TPEx (上櫃) institutional investors, per stock
    "tpex_3insti_daily_trading": "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading",
    "tpex_3insti_trading": "https://www.tpex.org.tw/openapi/v1/tpex_3insti_trading",
    # Shares outstanding (company profiles)
    "twse_t187ap03_L": "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
    "tpex_mopsfin_t187ap03_O": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
    # Per-stock daily OHLC / volume
    "twse_STOCK_DAY_ALL": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
    "tpex_mainboard_quotes": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes",
}

ROC_DATE = re.compile(r"^(\d{3})(\d{2})(\d{2})$")


def fetch(url):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def data_date(rows):
    """Return ISO date from the first row's ROC date field, if any."""
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return None
    for key in ("Date", "date", "出表日期", "資料日期"):
        value = str(rows[0].get(key, "")).strip()
        m = ROC_DATE.match(value)
        if m:
            y, mo, d = int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3))
            return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


def latest_hash(folder):
    if not os.path.isdir(folder):
        return None
    files = sorted(f for f in os.listdir(folder) if f.endswith(".json"))
    if not files:
        return None
    with open(os.path.join(folder, files[-1]), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    now = datetime.now(TPE)
    failures = []
    for i, (name, url) in enumerate(SOURCES.items()):
        if i:
            time.sleep(GAP_SECONDS)
        try:
            status, body = fetch(url)
            rows = json.loads(body.decode("utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {name}: {exc}")
            failures.append(name)
            continue
        canonical = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        folder = os.path.join(ROOT, name)
        digest = hashlib.sha256(canonical).hexdigest()
        if digest == latest_hash(folder):
            print(f"[SAME] {name}: unchanged ({len(rows) if isinstance(rows, list) else '?'} rows)")
            continue
        day = data_date(rows) or now.strftime("%Y-%m-%d")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{day}.json")
        with open(path, "wb") as fh:
            fh.write(canonical)
        print(f"[SAVE] {name}: {path} ({len(rows) if isinstance(rows, list) else '?'} rows, HTTP {status})")
    log = os.path.join(ROOT, "..", "fetch-log.tsv")
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(f"{now.isoformat(timespec='seconds')}\t{'FAIL:' + ','.join(failures) if failures else 'OK'}\n")
    return 1 if len(failures) == len(SOURCES) else 0


if __name__ == "__main__":
    sys.exit(main())
