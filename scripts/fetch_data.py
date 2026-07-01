"""pykrx 데이터 수집: 종목 종가, 지수 종가, 외국인 지분율.

주: pykrx는 정산 일봉(EOD) 데이터라 장중 갱신되지 않음 → 하루 1회 실행 전제.
성능: 종목 수백 개를 매 실행 전체 재수집. 느리면 build_json에서 캐시 최적화 검토(SPEC 참고).
"""
import time
from datetime import datetime, timedelta
import pandas as pd
from pykrx import stock
from config import HISTORY_DAYS, INDEX_CODE


def _date_range():
    today = datetime.now()
    frm = (today - timedelta(days=HISTORY_DAYS)).strftime("%Y%m%d")
    to = today.strftime("%Y%m%d")
    return frm, to


def get_index_close(market):
    """벤치마크 지수 종가 시계열(Series)."""
    frm, to = _date_range()
    code = INDEX_CODE[market]
    # 주: 구버전은 get_index_ohlcv_by_date(frm, to, code)
    df = stock.get_index_ohlcv(frm, to, code)
    return df["종가"].astype(float)


def get_stock_closes(tickers):
    """종목 종가 DataFrame(index=날짜, columns=티커). 실패 종목은 스킵."""
    frm, to = _date_range()
    closes = {}
    for i, t in enumerate(tickers):
        for attempt in range(3):
            try:
                df = stock.get_market_ohlcv(frm, to, t)
                if df is not None and not df.empty:
                    closes[t] = df["종가"].astype(float)
                break
            except Exception:
                time.sleep(1.0)
        if (i + 1) % 50 == 0:
            print(f"  ...종가 {i+1}/{len(tickers)}")
        time.sleep(0.05)
    return pd.DataFrame(closes)


def get_foreign_rate(tickers):
    """외국인 지분율 DataFrame(index=날짜, columns=티커). 없으면 해당 열 생략."""
    frm, to = _date_range()
    rates = {}
    for t in tickers:
        try:
            df = stock.get_exhaustion_rates_of_foreign_investment(frm, to, t)
            if df is not None and not df.empty and "지분율" in df.columns:
                rates[t] = df["지분율"].astype(float)
        except Exception:
            pass
        time.sleep(0.05)
    return pd.DataFrame(rates)
