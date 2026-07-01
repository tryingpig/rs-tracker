# RS 트래커 — 시장을 이기는 종목 (KOSPI200 / KOSDAQ150)

코스피200·코스닥150 구성종목 중 **시장을 이기는 종목**을 상대강도(RS)로 매 거래일 산출해
GitHub Pages 정적 페이지로 보여준다. 각 종목을 **시장 대비 + 섹터 대비 2단계**로 채점해
"진짜 대장"을 가려낸다.

## 구조
```
index.html                 프론트 (data/*.json 을 fetch)
data/kospi.json  kosdaq.json   파이프라인 산출물 (지금은 샘플)
data/sector_override.csv       yfinance 오류 교정용 (code,sec)
data/cache/                    섹터·가격 캐시
scripts/  config / universe / sectors / fetch_data / rs_engine / build_json
.github/workflows/update.yml   평일 18:30 KST 자동 갱신 + 월 1회 섹터 갱신
```

## 로컬 실행
```bash
pip install -r requirements.txt
python scripts/build_json.py            # data/kospi.json, kosdaq.json 생성
# 화면 미리보기 (file:// 는 fetch 불가 → 로컬 서버 필요)
python -m http.server 8000              # http://localhost:8000
```

## 만드는 순서 (체크포인트)
1. `python scripts/universe.py` → 구성종목이 나오는지. **✅ 체크: 종목 수 200/150.**
2. `python scripts/sectors.py` → 섹터 자동분류. 콘솔에 "미확인" 목록이 뜨면 그 코드들을
   `data/sector_override.csv`에 `code,sec`로 채운다. **✅ 체크: 미확인 20개 이내.**
3. `python scripts/build_json.py kospi` → `data/kospi.json` 생성. **✅ 체크: 상위에 강세 종목.**
4. 로컬 서버로 화면 확인. **✅ 체크: 목업과 동일하게 렌더.**
5. 코스닥 추가 후 토글 확인 → GitHub Pages 켜고 Actions `workflow_dispatch` 수동 실행.
6. 통과하면 cron 활성화.

## 알아둘 것 (한계)
- **EOD 데이터**: pykrx는 정산 일봉이라 장중 갱신 안 됨 → 하루 1회(18:30 KST).
- **섹터 분류**: yfinance(.KS/.KQ) 자동 + `sector_override.csv` 소수 교정. 월 1회 캐시.
  미확인 목록은 스크립트가 출력한다(주로 지주사·리츠·신규상장).
- **pykrx API**: 버전에 따라 함수 시그니처가 다를 수 있음(universe.py 주석 참고). 첫 실행에서 확인.
- **성능**: 종목 수백 개 전체 수집이라 첫 실행은 수 분 소요. 느리면 가격 캐시 도입(추후).
- 이 화면은 종목 추천이 아니라 시장 대비 강한 종목을 정량적으로 걸러 보여주는 분석 틀이다.
