#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""새로 생긴 '기타'(섹터 자동분류 실패) 종목을 'RS 섹터 보정 DB'에 자동 추가.

build_json.py 실행 후(data/{market}.json 생성 뒤)에 돌린다. 각 산출물의
unknown_sectors(=‘기타’ 종목코드) 중 DB에 아직 없는 것만 새 행으로 만든다.
- 새 행: 이름=종목명(참고용), 종목코드=코드, 섹터=빈칸, 활성=OFF.
  → 사용자가 나중에 섹터만 고르고 활성 체크하면 다음 갱신에 반영된다.
- 이미 있는 종목(이미 넣어둔/보정한 것)은 건너뛴다(중복 방지).
- 토큰: NOTION_TOKEN (Actions Secret). 실패해도 데이터 파이프라인을 막지 않도록 조용히 종료.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

DB_ID = "393ebba0843a80489747d6d5a651f6d6"  # RS 섹터 보정 DB
BASE = "https://api.notion.com/v1"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MARKETS = ("kospi", "kosdaq")


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


def collect_unknowns():
    """{code: 종목명} — 각 시장 산출물의 unknown_sectors 종목."""
    out = {}
    for mk in MARKETS:
        f = DATA_DIR / f"{mk}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        nm = {s["code"]: s.get("nm", s["code"]) for s in d.get("stocks", [])}
        for code in d.get("unknown_sectors", []):
            out[code] = nm.get(code, code)
    return out


def existing_codes(token):
    codes, cursor = set(), None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        res = api("POST", f"/databases/{DB_ID}/query", token, payload)
        for row in res["results"]:
            rt = row["properties"].get("종목코드", {}).get("rich_text", [])
            if rt:
                codes.add(rt[0]["plain_text"])
        if not res.get("has_more"):
            break
        cursor = res["next_cursor"]
    return codes


def title_key(token):
    db = api("GET", f"/databases/{DB_ID}", token)
    return next(k for k, v in db["properties"].items() if v["type"] == "title")


def main():
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("NOTION_TOKEN 없음 → 신규 기타 자동추가 건너뜀", file=sys.stderr)
        return

    unknowns = collect_unknowns()
    if not unknowns:
        print("unknown_sectors 없음 → 추가할 것 없음")
        return

    try:
        have = existing_codes(token)
        tkey = title_key(token)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"Notion 조회 실패({e}) → 건너뜀", file=sys.stderr)
        return

    new = {c: n for c, n in unknowns.items() if c not in have}
    if not new:
        print(f"신규 기타 없음 (전체 {len(unknowns)}종목 모두 DB에 존재)")
        return

    added = 0
    for code, name in sorted(new.items()):
        try:
            api("POST", "/pages", token, {
                "parent": {"database_id": DB_ID},
                "properties": {
                    tkey: {"title": [{"text": {"content": name}}]},
                    "종목코드": {"rich_text": [{"text": {"content": code}}]},
                    # 섹터는 빈칸(사용자가 선택), 활성 OFF
                    "활성": {"checkbox": False},
                },
            })
            print(f"  + {code} {name} (섹터 미지정·활성 OFF)")
            added += 1
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"  [실패] {code} {name}: {e}", file=sys.stderr)

    print(f"신규 기타 {added}종목 DB 추가 → Notion에서 섹터 지정 후 활성 체크 필요")


if __name__ == "__main__":
    main()
