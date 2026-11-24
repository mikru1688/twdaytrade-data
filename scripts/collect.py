#!/usr/bin/env python3
"""Collect daily after-hours open data (raw JSON) for TWDayTrade.

Only public open-data endpoints. Each source is saved as
data/raw/<source>/<YYYY-MM-DD>.json (data date when available, else Taipei fetch date).
A file is written only when the content differs from the latest saved file of that source.

Writes a run status to $STATUS_PATH (default: status.json) and exits:
  0 = OK, PENDING (data not published yet), HOLIDAY, SUSPECTED_CLOSED (unannounced closure, e.g. typhoon)
  1 = FAILED (fetch errors; a rerun may help)
  2 = INVALID (data anomaly; a rerun will not help)
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
UA = "twdaytrade-data-collector/1.1 (+https://github.com/mikru1688/twdaytrade-data)"
GAP_SECONDS = 5
BACKOFF = (10, 20, 40)
MIN_ROW_RATIO = 0.7  # rows below 70% of the previous file => INVALID
HOLIDAY_URL = "https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule"
# Daily market totals for the current month: lists the days the market actually traded.
TRADED_URL = "https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK"
SUSPECT_CLOSED_HOUR = 20  # from 20:00 Taipei, "nothing published today" means the market likely did not open

# kind "daily": data date must match the expected trading day; "profile": reference data.
SOURCES = {
    "tpex_3insti_daily_trading": ("daily", "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading"),
    "tpex_3insti_trading": ("daily", "https://www.tpex.org.tw/openapi/v1/tpex_3insti_trading"),
    "twse_STOCK_DAY_ALL": ("daily", "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"),
    "tpex_mainboard_quotes": ("daily", "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"),
    "twse_t187ap03_L": ("profile", "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"),
    "tpex_mopsfin_t187ap03_O": ("profile", "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"),
    # 集中市場漲跌證券數統計表: content stuck at 1150605 as of 2026-11-24; tracked to see whether it resumes.
    "twse_twtazu_od": ("profile", "https://openapi.twse.com.tw/v1/opendata/twtazu_od"),
}

ROC_DATE = re.compile(r"^(\d{3})(\d{2})(\d{2})$")


def roc_to_date(value):
    m = ROC_DATE.match(str(value).strip())
    if not m:
        return None
    return date(int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))


def fetch_json(url):
    last = None
    for attempt, wait in enumerate(BACKOFF, start=1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8-sig")), attempt
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < len(BACKOFF):
                time.sleep(wait)
    raise RuntimeError(f"{type(last).__name__}: {last}")


def data_date(rows):
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return None
    for key in ("Date", "date", "資料日期", "出表日期"):
        if key in rows[0]:
            return roc_to_date(rows[0][key])
    return None


def latest_file(folder):
    if not os.path.isdir(folder):
        return None
    files = sorted(f for f in os.listdir(folder) if f.endswith(".json"))
    return os.path.join(folder, files[-1]) if files else None


def non_trading_days():
    """Dates the TWSE market is closed (weekends handled separately)."""
    try:
        rows, _ = fetch_json(HOLIDAY_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] holiday schedule unavailable: {exc}")
        return set(), False
    closed = set()
    for row in rows:
        d = roc_to_date(row.get("Date", ""))
        text = f"{row.get('Name', '')}{row.get('Description', '')}"
        if d and "開始交易" not in text and "最後交易" not in text:
            closed.add(d)
    return closed, True


def traded_days():
    """Days the TWSE market actually traded (current month) from FMTQIK."""
    try:
        rows, _ = fetch_json(TRADED_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] FMTQIK unavailable: {exc}")
        return set()
    return {d for d in (roc_to_date(r.get("Date", "")) for r in rows if isinstance(r, dict)) if d}


def is_trading_day(d, closed, traded):
    """Scheduled trading day, minus days FMTQIK proves were skipped.

    A weekday is treated as an unannounced closure (e.g. typhoon) only when FMTQIK
    covers its month and already lists a later trading day, so publication lag is not misread.
    """
    if d.weekday() >= 5 or d in closed:
        return False
    if traded:
        latest = max(traded)
        if d.replace(day=1) == latest.replace(day=1) and d < latest and d not in traded:
            return False
    return True


def expected_trading_day(now, closed, traded):
    """After 14:00 Taipei: today if scheduled. Otherwise: the previous trading day."""
    today = now.date()
    if now.hour >= 14 and is_trading_day(today, closed, traded):
        return today
    d = today - timedelta(days=1)
    while not is_trading_day(d, closed, traded):
        d -= timedelta(days=1)
    return d


def main():
    now = datetime.now(TPE)
    closed, calendar_ok = non_trading_days()
    time.sleep(GAP_SECONDS)
    traded = traded_days()
    time.sleep(GAP_SECONDS)
    today = now.date()
    expected = expected_trading_day(now, closed, traded)
    holiday_today = now.hour >= 14 and not is_trading_day(today, closed, traded)

    results = []
    for i, (name, (kind, url)) in enumerate(SOURCES.items()):
        if i:
            time.sleep(GAP_SECONDS)
        item = {"source": name, "kind": kind, "status": "", "dataDate": None, "rows": None, "saved": False, "attempts": 0, "note": ""}
        results.append(item)
        try:
            rows, attempts = fetch_json(url)
            item["attempts"] = attempts
        except Exception as exc:  # noqa: BLE001
            item.update(status="FAILED", attempts=len(BACKOFF), note=str(exc)[:200])
            continue
        if not isinstance(rows, list) or not rows:
            item.update(status="INVALID", rows=0, note="empty or not a list")
            continue
        item["rows"] = len(rows)
        d = data_date(rows)
        item["dataDate"] = d.isoformat() if d else None
        folder = os.path.join(ROOT, name)
        prev = latest_file(folder)
        canonical = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if prev:
            with open(prev, "rb") as fh:
                prev_bytes = fh.read()
            prev_rows = len(json.loads(prev_bytes))
            if prev_rows and len(rows) < prev_rows * MIN_ROW_RATIO:
                item.update(status="INVALID", note=f"rows {len(rows)} < 70% of previous {prev_rows}")
                continue
            if hashlib.sha256(prev_bytes).digest() == hashlib.sha256(canonical).digest():
                item["note"] = "unchanged"
        if item["note"] != "unchanged":
            day = item["dataDate"] or now.strftime("%Y-%m-%d")
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, f"{day}.json"), "wb") as fh:
                fh.write(canonical)
            item["saved"] = True
        if kind == "daily" and d and d < expected:
            item["status"] = "PENDING"
        else:
            item["status"] = "OK"

    statuses = {r["status"] for r in results}
    daily = [r for r in results if r["kind"] == "daily" and r["status"] in ("OK", "PENDING")]
    nothing_today = bool(daily) and all(r["status"] == "PENDING" for r in daily)
    # Every daily source still shows an older day and FMTQIK has no entry for the expected day:
    # an unannounced closure (e.g. typhoon), not a failure. Same evening from 20:00, or the next morning.
    suspected_closed = (
        nothing_today
        and expected not in traded
        and (expected < today or now.hour >= SUSPECT_CLOSED_HOUR)
    )
    if "INVALID" in statuses:
        overall = "INVALID"
    elif "FAILED" in statuses:
        overall = "FAILED"
    elif holiday_today:
        overall = "HOLIDAY"
    elif suspected_closed:
        overall = "SUSPECTED_CLOSED"
    elif "PENDING" in statuses:
        overall = "PENDING"
    else:
        overall = "OK"

    status = {
        "overall": overall,
        "runAt": now.isoformat(timespec="seconds"),
        "expectedTradingDay": expected.isoformat(),
        "calendar": "ok" if calendar_ok else "unavailable",
        "tradedDaysThisMonth": len(traded),
        "todayTraded": today in traded,
        "sources": results,
    }
    with open(os.environ.get("STATUS_PATH", "status.json"), "w", encoding="utf-8") as fh:
        json.dump(status, fh, ensure_ascii=False, indent=2)
    for r in results:
        print(f"[{r['status']}] {r['source']}: date={r['dataDate']} rows={r['rows']} saved={r['saved']} {r['note']}")
    print(f"OVERALL {overall} (expected {expected.isoformat()})")
    return {"INVALID": 2, "FAILED": 1}.get(overall, 0)


if __name__ == "__main__":
    sys.exit(main())
