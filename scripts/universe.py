"""지수 구성종목(유니버스) 조회."""
from pykrx import stock
from config import INDEX_CODE


def get_universe(market):
    """(tickers, names) 반환. tickers=구성종목 코드 리스트, names={code: 종목명}."""
    code = INDEX_CODE[market]
    # 주: pykrx 버전에 따라 시그니처가 다를 수 있음.
    #   구버전: get_index_portfolio_deposit_file(date, ticker)
    #   신버전: get_index_portfolio_deposit_file(ticker)
    # 첫 실행에서 에러가 나면 인자 순서를 확인할 것.
    tickers = stock.get_index_portfolio_deposit_file(code)
    tickers = [t for t in tickers if t]  # 방어
    names = {}
    for t in tickers:
        try:
            names[t] = stock.get_market_ticker_name(t)
        except Exception:
            names[t] = t
    return tickers, names


if __name__ == "__main__":
    for mk in ("kospi", "kosdaq"):
        ts, nm = get_universe(mk)
        print(f"[{mk}] {len(ts)}종목  예: {ts[:3]} -> {[nm[t] for t in ts[:3]]}")
