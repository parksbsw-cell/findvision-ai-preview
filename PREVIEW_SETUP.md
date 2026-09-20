# ClueSight 배포 확인

기존 서비스 URL과 저장소를 유지합니다. 다른 Streamlit 앱은 변경하지 않습니다.

- Repository: parksbsw-cell/findvision-ai-preview
- Branch: main
- Main file: app.py
- URL: https://findvision-ai-preview-cckvydwon3usuw6iys7jma.streamlit.app/

Manage app에서 위 배포 경로를 확인합니다. main 변경 후 자동 재배포된 화면에
ClueSight 및 버전 2026.09.20이 표시되는지 확인합니다.

기존 CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN Secrets는 유지합니다.
통계의 추가 Secrets 및 SQL 적용은 ANALYTICS_SETUP.md에 설명되어 있습니다.
설정 전에는 전체 통계를 임의 숫자로 표시하지 않습니다.

## 실제 점검
1. 가상 성인 인물 설명으로 빠른 생성을 실행하고 검수 호출 없이 결과와 측정 시간이 표시되는지 확인합니다.
2. 하단 다시 생성하기를 눌러 새 결과와 브라우저 완료 횟수 증가를 확인합니다.
3. 정밀 생성을 실행하고 768×1024 결과, 시도 수와 검수 결과를 확인합니다.
4. 원문 보기 등 화면 상태가 변해도 결과와 완료 횟수가 유지되는지 확인합니다.
5. 안전 검사에 막히면 차단 안내를 확인합니다. 자동 우회 재시도는 하지 않습니다.

문제 발생 시 검증된 이전 커밋으로 되돌리는 커밋을 main에 적용합니다.
DB 설정을 되돌릴 때는 CLUESIGHT_ANALYTICS_ENABLED를 false로 바꾸면 됩니다.
기존 analytics_events 테이블은 새 통계 설정의 영향을 받지 않습니다.
