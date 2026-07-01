"""RS 엔진: 종목별 상대강도 지표 계산.

정의:
- ret(series, n) = 최근 n거래일 수익률 (트레일링)
- rel_n = ret(종목,n) - ret(지수,n)  → 초과수익
- RS 점수 = 가중합(rel_5,rel_21,rel_63,rel_126) → 유니버스 내 퍼센타일(1~99)
- 주간초과=rel_5, 월간초과=rel_21
- 섹터초과 = 종목수익 - 같은 섹터 평균수익
- 이긴 주 = 최근 12개 완결주(W-FRI)에서 종목 주간수익 > 지수 주간수익 수
- spark = (종목/지수) 비율선 최근 12주 표본, 시작=100
- ff = 외국인 지분율 최근 20거래일 변화(%p)
"""
import numpy as np
import pandas as pd
from config import RS_WEIGHTS, W_WEEK, W_MONTH, FF_WINDOW, WEEKS_WIN, UNKNOWN_SECTOR


def _ret(series, n):
    s = series.dropna()
    if len(s) <= n:
        return np.nan
    return float(s.iloc[-1] / s.iloc[-1 - n] - 1.0)


def compute(closes_df, index_close, sectors, foreign_df):
    """종목 레코드 리스트와 벤치마크 요약을 반환."""
    closes_df = closes_df.sort_index()
    bench = index_close.sort_index().reindex(closes_df.index).ffill()

    bench_ret = {n: _ret(bench, n) for n in (5, 21, 63, 126)}

    # 종목별 트레일링 수익률
    recs = {}
    for t in closes_df.columns:
        s = closes_df[t]
        r = {n: _ret(s, n) for n in (5, 21, 63, 126)}
        if any(pd.isna(v) for v in r.values()):
            continue
        rel = {n: r[n] - bench_ret[n] for n in (5, 21, 63, 126)}
        score = sum(RS_WEIGHTS[n] * rel[n] for n in RS_WEIGHTS)
        recs[t] = {"ret": r, "rel": rel, "score": score}

    valid = list(recs.keys())
    if not valid:
        return [], _bench_summary(bench, bench_ret)

    # RS 퍼센타일 (1~99)
    scores = pd.Series({t: recs[t]["score"] for t in valid})
    pct = scores.rank(pct=True)  # 0..1

    # 섹터 그룹 & 섹터 평균수익(윈도우별)
    sec_of = pd.Series({t: sectors.get(t, UNKNOWN_SECTOR) for t in valid})
    sec_mean = {}
    for n in (W_WEEK, W_MONTH):
        rr = pd.Series({t: recs[t]["ret"][n] for t in valid})
        sec_mean[n] = rr.groupby(sec_of).mean()

    # 섹터 내 RS 순위
    srank = {}
    for sec, grp in sec_of.groupby(sec_of):
        members = sorted(grp.index, key=lambda x: recs[x]["score"], reverse=True)
        for i, t in enumerate(members):
            srank[t] = (i + 1, len(members))

    # 주간 승패 (완결주)
    wk_stock = closes_df[valid].resample("W-FRI").last().pct_change()
    wk_bench = bench.resample("W-FRI").last().pct_change()
    recent_s = wk_stock.tail(WEEKS_WIN)
    recent_b = wk_bench.tail(WEEKS_WIN)
    win = {t: int((recent_s[t] > recent_b).sum()) for t in valid}

    # RS 비율선 spark (최근 12주)
    ratio = closes_df[valid].div(bench, axis=0)
    wk_ratio = ratio.resample("W-FRI").last().tail(12)

    # 외국인 지분율 변화
    ff = {}
    for t in valid:
        if foreign_df is not None and t in foreign_df.columns:
            s = foreign_df[t].dropna()
            if len(s) > FF_WINDOW:
                ff[t] = round(float(s.iloc[-1] - s.iloc[-1 - FF_WINDOW]), 2)

    out = []
    for t in valid:
        r = recs[t]
        sec = sec_of[t]
        wSec = (r["ret"][W_WEEK] - sec_mean[W_WEEK].get(sec, 0.0)) * 100
        mSec = (r["ret"][W_MONTH] - sec_mean[W_MONTH].get(sec, 0.0)) * 100
        col = wk_ratio[t].dropna()
        spark = _normalize_spark(col.tolist())
        rk, n = srank.get(t, (1, 1))
        out.append({
            "code": t,
            "sec": sec,
            "rs": int(round(pct[t] * 98)) + 1,
            "wMkt": round(r["rel"][W_WEEK] * 100, 1),
            "mMkt": round(r["rel"][W_MONTH] * 100, 1),
            "wSec": round(wSec, 1),
            "mSec": round(mSec, 1),
            "win": win.get(t, 0),
            "srank": f"{rk}/{n}",
            "ff": ff.get(t, 0.0),
            "spark": spark,
        })

    out.sort(key=lambda d: d["rs"], reverse=True)
    return out, _bench_summary(bench, bench_ret)


def _normalize_spark(vals):
    vals = [v for v in vals if v == v]  # NaN 제거
    if not vals:
        return []
    base = vals[0] or 1.0
    return [round(v / base * 100, 2) for v in vals]


def _bench_summary(bench, bench_ret):
    b = bench.dropna()
    return {
        "close": round(float(b.iloc[-1]), 2) if len(b) else None,
        "retW": round((bench_ret[5] or 0) * 100, 1),
        "retM": round((bench_ret[21] or 0) * 100, 1),
    }
