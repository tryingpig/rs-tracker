"""공통 설정값. 지수코드/윈도우/가중치/경로 등."""

# 시장별 벤치마크 지수 코드 (pykrx). 첫 실행 시 실제 pykrx 버전으로 확인.
INDEX_CODE = {"kospi": "1028", "kosdaq": "2203"}
BENCH_NAME = {"kospi": "코스피200", "kosdaq": "코스닥150"}
MARKET_LABEL = {"kospi": "KOSPI200", "kosdaq": "KOSDAQ150"}

# yfinance 티커 접미사: 코스피 .KS / 코스닥 .KQ
YF_SUFFIX = {"kospi": ".KS", "kosdaq": ".KQ"}

# 히스토리: 6개월(126거래일)을 안전하게 담기 위해 여유 있는 달력일수를 받는다.
HISTORY_DAYS = 300

# 트레일링 윈도우(거래일). 요일과 무관하게 오늘부터 거꾸로 센 구간.
# W_DAY=1(일간)은 표시용 지표(일간초과)일 뿐, RS 점수 가중(RS_WEIGHTS)에는 포함하지 않는다.
W_DAY, W_WEEK, W_MONTH, W_3M, W_6M = 1, 5, 21, 63, 126
RS_WEIGHTS = {5: 0.15, 21: 0.40, 63: 0.30, 126: 0.15}

FF_WINDOW = 20        # 외국인 지분율 변화 측정 구간(거래일)
WEEKS_WIN = 12        # '이긴 주' 집계 대상 주 수

# 경로
DATA_DIR = "data"
CACHE_DIR = "data/cache"
OVERRIDE_CSV = "data/sector_override.csv"
SECTOR_CACHE = "data/cache/sectors_{market}.json"
OUT_JSON = "data/{market}.json"

# Yahoo 섹터명 → 한글(GICS 11개)
YAHOO_SECTOR_KO = {
    "Technology": "정보기술",
    "Financial Services": "금융",
    "Healthcare": "헬스케어",
    "Consumer Cyclical": "경기소비재",
    "Consumer Defensive": "필수소비재",
    "Industrials": "산업재",
    "Basic Materials": "소재",
    "Energy": "에너지",
    "Utilities": "유틸리티",
    "Real Estate": "부동산",
    "Communication Services": "커뮤니케이션",
}
SECTORS_KO = list(YAHOO_SECTOR_KO.values())
UNKNOWN_SECTOR = "기타"
