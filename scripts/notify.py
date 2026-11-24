#!/usr/bin/env python3
"""Build the status comment (Markdown) from status.json for the Collector status issue."""
import json
import os
import sys

LABEL = {"OK": "✅ OK", "PENDING": "⏳ 待更新", "HOLIDAY": "🛌 休市", "FAILED": "❌ 失敗", "INVALID": "⚠️ 資料異常", "SUSPECTED_CLOSED": "🌀 疑似休市（未預告）", "": "—"}


def main():
    path = os.environ.get("STATUS_PATH", "status.json")
    run_url = os.environ.get("RUN_URL", "")
    attempt = os.environ.get("RUN_ATTEMPT", "1")
    slot = os.environ.get("SLOT", "manual")
    commit = os.environ.get("COMMIT_RESULT", "unknown")
    job = os.environ.get("JOB_STATUS", "")
    try:
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
    except Exception:  # noqa: BLE001
        print(f"### ❌ 失敗（collector 未產生狀態）\n\n- 時段：{slot}\n- 第 {attempt} 次執行\n- job：{job}\n- [run]({run_url})")
        return 0
    lines = [
        f"### {LABEL.get(st['overall'], st['overall'])}｜預期資料日 {st['expectedTradingDay']}",
        "",
        f"- 時段：{slot}；執行時間：{st['runAt']}；第 {attempt} 次執行",
        f"- commit：{commit}；休市日曆：{st['calendar']}；本月實際交易日 {st.get('tradedDaysThisMonth', '?')} 天；今日有交易：{'是' if st.get('todayTraded') else '否／未公布'}",
        f"- [run]({run_url})",
        "",
        "| 來源 | 狀態 | 資料日 | 列數 | 存檔 | 備註 |",
        "|---|---|---|---|---|---|",
    ]
    for s in st["sources"]:
        lines.append(f"| `{s['source']}` | {LABEL.get(s['status'], s['status'])} | {s['dataDate'] or '—'} | {s['rows'] if s['rows'] is not None else '—'} | {'是' if s['saved'] else '否'} | {s['note'] or ''} |")
    if st["overall"] == "SUSPECTED_CLOSED":
        lines += ["", "> 未預告的休市（例如颱風）：預期資料日沒有任何每日資料，FMTQIK 也沒有該日。不重跑；FMTQIK 之後列出更晚的交易日時，該日會自動視為休市。"]
    elif st["overall"] == "INVALID":
        lines += ["", "> 資料格式或筆數異常，未存檔。重跑通常無效，需要檢查來源或修改 collector。"]
    elif st["overall"] == "FAILED":
        lines += ["", "> 抓取失敗；30 分鐘後自動重跑（最多 2 次）。"]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
