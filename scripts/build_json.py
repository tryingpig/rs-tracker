"""오케스트레이터: 유니버스 → 섹터 → 데이터 → RS → data/{market}.json.

실행: python scripts/build_json.py            (kospi, kosdaq 모두)
      python scripts/build_json.py kospi      (특정 시장만)
      python scripts/build_json.py --refresh-sectors   (섹터 캐시 강제 갱신, 월 1회)
"""
import json
import os
import sys
import tempfile
from datetime import datetime

from config import (DATA_DIR, OUT_JSON, BENCH_NAME, MARKET_LABEL, INDEX_CODE)
from universe import get_universe
from sectors import classify
from fetch_data import get_index_close, get_stock_closes, get_foreign_rate
from rs_engine import compute


def _now_kst():
    # Actions는 UTC. 표시용 KST = UTC+9.
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        from datetime import timedelta
        return (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")


def build_market(market, refresh_sectors=False):
    print(f"=== {market} 시작 ===")
    tickers, names = get_universe(market)
    print(f"유니버스 {len(tickers)}종목")

    sectors, unknown = classify(market, tickers, refresh=refresh_sectors)

    index_close = get_index_close(market)
    closes = get_stock_closes(tickers)
    foreign = get_foreign_rate(tickers)
    print(f"종가 {closes.shape[1]}종목 / 외국인 {foreign.shape[1]}종목")

    stocks, bench = compute(closes, index_close, sectors, foreign)
    for s in stocks:
        s["nm"] = names.get(s["code"], s["code"])

    payload = {
        "market": market,
        "label": MARKET_LABEL[market],
        "benchmark": {
            "name": BENCH_NAME[market],
            "code": INDEX_CODE[market],
            "close": bench["close"],
            "retW": bench["retW"],
            "retM": bench["retM"],
        },
        "updated_at": _now_kst(),
        "universe_count": len(tickers),
        "unknown_sectors": unknown,
        "stocks": stocks,
    }
    _atomic_write(OUT_JSON.format(market=market), payload)
    print(f"=== {market} 완료: {len(stocks)}종목 기록 ===")


def _atomic_write(path, payload):
    """검증 통과분만 원자적으로 교체(부분 실패 시 기존 JSON 유지)."""
    if not payload["stocks"]:
        print(f"[경고] {path}: 종목 0개 → 기존 파일 유지, 쓰지 않음")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def main():
    args = [a for a in sys.argv[1:]]
    refresh = "--refresh-sectors" in args
    args = [a for a in args if not a.startswith("--")]
    markets = args if args else ["kospi", "kosdaq"]
    for mk in markets:
        try:
            build_market(mk, refresh_sectors=refresh)
        except Exception as e:
            print(f"[에러] {mk} 실패: {e}")


if __name__ == "__main__":
    main()
