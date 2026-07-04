#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notion 'RS 섹터 보정 DB' → data/sector_override.csv 생성 (rs-tracker 전용).

섹터 자동분류(yfinance GICS)가 비우거나 틀린 종목을 손으로 교정하는 override를
전용 Notion DB에서 받아 data/sector_override.csv(code,sec)로 쓴다. build_json.py가
섹터 분류 시 이 CSV를 최우선으로 읽는다(scripts/sectors.py).

- DB 스키마: 이름(종목명, 참고용) · 종목코드(6자리) · 섹터(GICS 11 택1) · 활성(체크).
- 대상: 활성=True 행. code=종목코드, sec=섹터.
- 토큰: 환경변수 NOTION_TOKEN (Actions Secret).
- Notion 조회 실패 시: 기존 CSV가 있으면 유지(폴백), 없으면 헤더만이라도 생성.
"""
import csv
import io
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

DB_ID = "393ebba0843a80489747d6d5a651f6d6"  # RS 섹터 보정 DB(rs-tracker 전용, ETF Sector DB와 별도)
BASE = "https://api.notion.com/v1"
OUT = Path(__file__).resolve().parent.parent / "data" / "sector_override.csv"


def api(method, path, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def _rt(prop):
    if not prop:
        return ""
    arr = prop.get("rich_text") or prop.get("title") or []
    return "".join(t.get("plain_text", "") for t in arr).strip()


def fetch_overrides(token):
    rows, cursor = [], None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        res = api("POST", f"/databases/{DB_ID}/query", token, payload)
        for r in res["results"]:
            p = r["properties"]
            active = p.get("활성", {}).get("checkbox", False)
            if active:
                code = _rt(p.get("종목코드")).split(".")[0].strip()
                sec = (p.get("섹터", {}).get("select") or {}).get("name", "").strip()
                if code and sec:
                    rows.append((code, sec))
        if not res.get("has_more"):
            break
        cursor = res["next_cursor"]
    rows.sort()
    return rows


def write_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["code", "sec"])
    for code, sec in rows:
        w.writerow([code, sec])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())


def main():
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        if OUT.exists():
            print("NOTION_TOKEN 없음 → 기존 sector_override.csv 유지(폴백)", file=sys.stderr)
            return
        write_csv([])
        print("NOTION_TOKEN 없음 → 빈 override CSV 생성")
        return

    try:
        rows = fetch_overrides(token)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        if OUT.exists():
            print(f"Notion 조회 실패({e}) → 기존 CSV 유지(폴백)", file=sys.stderr)
            return
        write_csv([])
        print(f"Notion 조회 실패({e}) → 빈 override CSV 생성", file=sys.stderr)
        return

    write_csv(rows)
    print(f"sector_override.csv 생성: override {len(rows)}개")


if __name__ == "__main__":
    main()
