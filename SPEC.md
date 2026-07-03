# RS 트래커 빌드 스펙 (최종)

프론트(`index.html`)와 파이프라인(`scripts/`)의 계약 문서. 코드는 이 스펙을 따른다.

## 1. 목표 · 성공 기준
코스피200·코스닥150에서 시장을 이기는 종목을 RS로 매 거래일 산출, GitHub Pages로 표시.
완료 조건: `data/*.json`이 pykrx 실데이터로 자동 생성 → 프론트가 fetch해 렌더 → Actions가 평일 정산 후 갱신·커밋.
비목표: forward PER, 장중 실시간, 매매신호, 백테스트.

## 2. 아키텍처
`Actions(18:30 KST) → build_json.py[universe→sectors→fetch_data→rs_engine] → data/{market}.json → index.html`

## 3. 도구 계약
- pykrx: `get_index_portfolio_deposit_file`(구성종목), `get_index_ohlcv`(지수), `get_market_ohlcv`(종목),
  `get_exhaustion_rates_of_foreign_investment`(외국인 지분율), `get_market_ticker_name`.
  지수코드 코스피200=1028, 코스닥150=2203. 날짜 `YYYYMMDD`. 히스토리 약 300일.
- yfinance: `Ticker(code+suffix).info["sector"]`, 접미사 코스피 `.KS` / 코스닥 `.KQ`.

## 4. 데이터 스키마 — `data/{market}.json`
```json
{
  "market":"kospi","label":"KOSPI200",
  "benchmark":{"name":"코스피200","code":"1028","close":352.4,"retD":0.4,"retW":2.1,"retM":5.4},
  "updated_at":"2026-07-01 18:30","universe_count":200,"unknown_sectors":[],
  "stocks":[{"nm":"SK하이닉스","code":"000660","sec":"정보기술","rs":94,
    "dMkt":0.8,"wMkt":4.2,"mMkt":42.5,"dSec":0.5,"wSec":3.6,"mSec":14.2,"win":10,"srank":"1/18","ff":1.4,"spark":[100,...]}]
}
```
`benchmark.retW/retM`=지수 자체의 주간/월간 수익률(초과수익의 기준, 헤더에 표시).
프론트는 tiles·이긴종목수를 stocks에서 기간별로 계산.

## 5. RS 엔진 규칙 (rs_engine.py)
윈도우(트레일링 거래일): 일=1, 주=5, 월=21, 3M=63, 6M=126. `ret(s,n)=s[-1]/s[-1-n]-1`, `rel_n=ret(종목)-ret(지수)`.
- RS점수 = 0.15·rel_5 + 0.40·rel_21 + 0.30·rel_63 + 0.15·rel_126 → 유니버스 퍼센타일 1~99(`rs`). (일간 rel_1은 표시용, 점수 미포함)
- 일간초과 `dMkt`=rel_1·100, 주간초과 `wMkt`=rel_5·100, 월간초과 `mMkt`=rel_21·100. (지수 자체 수익률 `retD/retW/retM`은 헤더 기준선)
- 섹터초과 `dSec/wSec/mSec` = 종목수익 − 같은 섹터 평균수익(각 1/5/21일). `srank` = 섹터 내 RS점수 순위.
- 이긴 주 `win` = 최근 12개 완결주(W-FRI)에서 종목 주간수익 > 지수 주간수익 수.
- `spark` = (종목/지수) 비율선 최근 12주, 시작=100. `ff` = 외국인 지분율 최근 20거래일 변화(%p).
- 판정(프론트): wMkt·wSec(또는 mMkt·mSec) 부호 → 진짜대장/시장우위/섹터우위/약세.

## 6. 섹터 (핵심 결정)
분류 = **yfinance 자동 + override CSV + 월 1회 캐시**. 우선순위 override > 캐시 > yfinance.
Yahoo 영문 섹터 → 한글 GICS 11(정보기술·금융·헬스케어·경기소비재·필수소비재·산업재·소재·에너지·유틸리티·부동산·커뮤니케이션).
yfinance가 비운 종목은 `기타`로 두고 `unknown` 목록 출력 → `sector_override.csv`에 교정.
RS의 섹터 벤치마크는 "코스피200 내 같은 섹터 종목 평균"(미국 SPDR ETF 아님). 라벨만 disparity와 공유.

## 7. 가드레일
- 하루 1회(EOD). 휴장·주말은 `git diff --staged --quiet`로 빈 커밋 스킵.
- pykrx 종목 수집 재시도(3회), 실패 종목 스킵(전체 실패 방지).
- `build_json`은 종목 0개면 기존 JSON 유지(원자적 교체).
- 섹터 미확인은 `기타` + 로그 경고.

## 8. ADR
벤치=지수레벨(1028/2203). 홈지수 기준(시장 혼합 안 함). 2단계 채점으로 "대장" 판별.
forward PER 제외. 한 페이지+시장 토글. 색: 진짜대장=빨강/시장우위=노랑/섹터우위=주황/약세=파랑, 등락은 빨강+·파랑−.
갱신 주기 = 18:30 KST 1회(20분 주기는 EOD 데이터라 무의미). 섹터 = yfinance 자동(수동 CSV 폐기, override만 유지).
