"""섹터 자동분류: yfinance(.KS/.KQ) → 한글 GICS 11섹터.

우선순위: override CSV > 캐시 > yfinance 조회.
- override CSV(data/sector_override.csv): yfinance가 비우거나 틀린 소수 종목을 손으로 교정.
- 캐시(data/cache/sectors_{market}.json): 섹터는 자주 안 바뀌므로 월 1회만 refresh.
- 조회 실패 종목은 '기타'로 두고 unknown 목록으로 리턴 → 이 목록을 채우면 됨.
"""
import csv
import json
import os
import time
import yfinance as yf
from config import YF_SUFFIX, YAHOO_SECTOR_KO, OVERRIDE_CSV, SECTOR_CACHE, UNKNOWN_SECTOR


def _load_override():
    m = {}
    if os.path.exists(OVERRIDE_CSV):
        with open(OVERRIDE_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                code = (row.get("code") or "").strip()
                sec = (row.get("sec") or "").strip()
                if code and sec:
                    m[code] = sec
    return m


def _fetch_yahoo_sector(code, market, retries=2):
    sym = code + YF_SUFFIX[market]
    for _ in range(retries + 1):
        try:
            info = yf.Ticker(sym).info or {}
            en = info.get("sector")
            if en:
                return YAHOO_SECTOR_KO.get(en, UNKNOWN_SECTOR)
            return None
        except Exception:
            time.sleep(1.0)
    return None


def classify(market, tickers, refresh=False):
    """{code: 한글섹터}, unknown(list) 반환."""
    cache_path = SECTOR_CACHE.format(market=market)
    cache = {}
    if os.path.exists(cache_path) and not refresh:
        try:
            cache = json.load(open(cache_path, encoding="utf-8"))
        except Exception:
            cache = {}

    override = _load_override()
    result, unknown = {}, []

    for code in tickers:
        if code in override:
            result[code] = override[code]
            continue
        cached = cache.get(code)
        if cached and cached != UNKNOWN_SECTOR:
            result[code] = cached
            continue
        sec = _fetch_yahoo_sector(code, market)
        if sec:
            result[code] = sec
        else:
            result[code] = UNKNOWN_SECTOR
            unknown.append(code)
        cache[code] = result[code]
        time.sleep(0.4)  # 레이트리밋 회피

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    if unknown:
        print(f"[{market}] 섹터 미확인 {len(unknown)}종목 → sector_override.csv에 채울 것:")
        print("  " + ", ".join(unknown))
    return result, unknown


if __name__ == "__main__":
    from universe import get_universe
    for mk in ("kospi", "kosdaq"):
        ts, _ = get_universe(mk)
        secs, unk = classify(mk, ts, refresh=True)
        print(f"[{mk}] 분류완료 {len(secs)} / 미확인 {len(unk)}")
