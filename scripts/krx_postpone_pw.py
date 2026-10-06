"""KRX 비밀번호 변경 요구(CD010)를 '90일 뒤에 다시 알림'으로 자동 연장한다.

data.krx.co.kr 은 일정 주기마다 로그인 응답으로 CD010(패스워드 변경 필요)을 돌려주고,
그동안 pykrx 로그인이 막혀 지수·구성종목 조회가 전부 실패한다(2026-09-30~10-06 실제 발생).
사이트 로그인 화면의 '90일 뒤에 다시 알림' 버튼은 같은 세션으로
postponePasswordChange.cmd 를 POST 하는 것뿐이라(login.jsp·mdc.layer.js 확인) 그대로 재현한다.

build 전에 한 번 돌린다. 여기서 실패해도 job 은 멈추지 않고 build 로그로 넘긴다.
"""
import os
import sys

import requests

BASE = "https://data.krx.co.kr/contents/MDC/COMS/client"
LOGIN_PAGE = f"{BASE}/MDCCOMS001.cmd"
LOGIN_JSP = f"{BASE}/view/login.jsp?site=mdc"
LOGIN_URL = f"{BASE}/MDCCOMS001D1.cmd"
POSTPONE_URL = f"{BASE}/postponePasswordChange.cmd"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def login(s, mbr_id, pw):
    s.get(LOGIN_PAGE, headers={"User-Agent": UA}, timeout=15)
    s.get(LOGIN_JSP, headers={"User-Agent": UA, "Referer": LOGIN_PAGE}, timeout=15)
    payload = {"mbrNm": "", "telNo": "", "di": "", "certType": "",
               "mbrId": mbr_id, "pw": pw}
    headers = {"User-Agent": UA, "Referer": LOGIN_PAGE}
    data = s.post(LOGIN_URL, data=payload, headers=headers, timeout=15).json()
    if data.get("_error_code") == "CD011":  # 중복 로그인
        payload["skipDup"] = "Y"
        data = s.post(LOGIN_URL, data=payload, headers=headers, timeout=15).json()
    return data.get("_error_code", ""), data.get("_error_message", "")


def main():
    mbr_id, pw = os.getenv("KRX_ID"), os.getenv("KRX_PW")
    if not (mbr_id and pw):
        print("KRX_ID/KRX_PW 없음 — 연장 점검 생략")
        return

    s = requests.Session()
    code, msg = login(s, mbr_id, pw)
    if code != "CD010":
        print(f"KRX 비밀번호 연장 불필요 (로그인 응답 {code or '-'} {msg})")
        return

    print(f"KRX 비밀번호 변경 요구 감지({msg}) → 90일 연장 요청")
    resp = s.post(POSTPONE_URL, timeout=15,
                  headers={"User-Agent": UA, "Referer": LOGIN_JSP,
                           "X-Requested-With": "XMLHttpRequest"})
    print(f"  연장 응답 {resp.status_code}: {resp.text[:200]}")

    code, msg = login(requests.Session(), mbr_id, pw)
    if code == "CD001":
        print("  연장 완료 — 재로그인 정상(CD001)")
    else:
        # ::warning:: 은 Actions 요약에 노출된다
        print(f"::warning::KRX 비밀번호 연장 실패 — 재로그인 응답 {code} {msg}. "
              "data.krx.co.kr 에서 직접 '90일 뒤에 다시 알림'을 눌러야 함")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # 연장 점검 실패가 build 를 막지 않게
        print(f"::warning::KRX 비밀번호 연장 점검 오류: {e!r}")
    sys.exit(0)
