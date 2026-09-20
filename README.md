# ClueSight

실종 재난문자의 인상착의를 분석하여 전신 참고 이미지를 만드는 Streamlit 앱입니다.
생성 이미지는 실제 얼굴 복원이나 신원 확인 자료가 아닙니다.

서비스: https://findvision-ai-preview-cckvydwon3usuw6iys7jma.streamlit.app/
배포 소스: parksbsw-cell/findvision-ai-preview, main, app.py

## 기능
- 재난문자 원문에서 명시된 한국어 머리 스타일·체형·의류·소지품을 분석합니다.
- 의류 브랜드를 괄호에 표시하고 다른 옷으로 브랜드가 전파되는 것을 방지합니다.
- 마지막 목격 위치와 발송 지역을 각각 표시합니다. 이미지 조건은 구조화된 외형 항목에서 다시 만듭니다.
- 빠른 생성: 512×768 이미지 1회를 생성하며 속도를 위해 자동 검수를 생략합니다.
- 정밀 생성: 768×1024 이미지, 검수 결과에 따라 최대 3회 생성.
- 첫 이미지와 검수 완료까지의 시간을 요청마다 측정합니다. 속도나 정확도 향상을 보장하지 않습니다.
- 자동 검수 불가 또는 후속 생성 실패에도 앞선 이미지를 보존합니다.
- 결과와 하단 재생성 버튼은 화면 재실행 후에도 유지합니다.
- 브라우저 완료 횟수를 쿠키로 보관합니다(1년, 기기별, 쿠키 삭제 시 초기화 가능).
- 별도 Supabase 테이블을 설정하면 누적 생성·익명 브라우저·한국 날짜 기준 재방문을 SQL로 집계합니다.

이미지 제공자의 안전 검사 차단을 자동 우회하거나 재시도하지 않습니다.
외형 추출과 이미지 검수에는 모델 오류가 있을 수 있습니다.
한 번의 완료는 최대 3회 생성 중 선택된 결과 1건입니다. 검수 불가라도 이미지를 받으면 완료입니다.

## 실행
```sh
pip install -r requirements-dev.txt
streamlit run app.py
python -m pytest -q
ruff check .
```

Cloudflare 설정은 Streamlit Secrets의 CLOUDFLARE_ACCOUNT_ID와 CLOUDFLARE_API_TOKEN에 넣습니다.
키는 소스에 저장하지 않습니다. 전체 통계는 [ANALYTICS_SETUP.md](ANALYTICS_SETUP.md)를 따릅니다.
배포 확인은 [PREVIEW_SETUP.md](PREVIEW_SETUP.md)를 참고하세요.

## 검증 범위
테스트는 네트워크 응답을 대체하여 재생성·예외 처리·모드별 호출 수·브랜드 연결·위치 제외·집계
payload를 검사합니다. 실제 API 성공이나 이미지 정확도·지연 시간의 개선을 증명하지 않습니다.
Supabase SQL은 실제 프로젝트 적용 후 접근 권한과 집계 결과를 추가 확인해야 합니다.
