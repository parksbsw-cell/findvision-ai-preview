# ClueSight 전체 통계 연결

설정 전 통계는 비활성화됩니다. 기존 analytics_events는 읽거나 변경하지 않습니다.

1. 사용할 Supabase 프로젝트 SQL Editor에서 supabase_setup.sql을 실행합니다.
2. 해당 Streamlit 앱의 Manage app → Settings → Secrets에 아래 항목을 추가합니다.
   기존 Cloudflare 설정은 유지합니다. 실제 값은 GitHub나 대화에 붙여 넣지 마세요.

```toml
CLUESIGHT_ANALYTICS_ENABLED = "true"
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SECRET_KEY = "YOUR_SERVER_SECRET_KEY"
ADMIN_PASSWORD = "YOUR_PRIVATE_ADMIN_PASSWORD"
```

서버 전용 sb_secret_… 또는 legacy service_role 키를 사용합니다. anon/publishable 키는
사용하지 않습니다. 일반 SUPABASE_KEY는 다른 환경에 잘못 연결하지 않도록 읽지 않습니다.

3. 이미지 생성 후 관리자 통계를 열어 총 완료 수가 1 증가하는지 확인합니다.
   단순 화면 재실행은 중복 저장되지 않아야 합니다.
4. 다른 브라우저의 생성은 생성 브라우저 수를 늘립니다. 다른 한국 날짜에 다시 생성하면
   재방문 수가 늘어납니다. 연결 실패 시 0으로 가장하지 않고 오류를 표시합니다.

집계 단위는 결과 1건(최대 3회 생성 포함)입니다. 검수 실패도 이미지 결과를 받으면 완료입니다.
생성 자체 실패는 집계하지 않습니다. 원문·이름·장소·이미지·IP는 저장하지 않고 익명 UUID,
시간, 모드, 시도 횟수, 자동 검수 결과만 저장합니다. 익명 브라우저 수는 실제 사람 수가 아닙니다.
쿠키 삭제·시크릿 모드·다른 기기는 별도입니다. 개인 완료 횟수는 쿠키 기반 참고값입니다.

누적 집계는 SQL에서 수행하므로 10,000건 제한이 없습니다. RLS를 켜고 anon/authenticated
역할의 읽기·쓰기·집계 함수 실행을 차단합니다. 저장 장애는 이미지 기능을 중단시키지 않고
해당 결과에 저장 실패를 표시합니다. 설정 이전 사용량은 소급 복원할 수 없습니다.
끄려면 CLUESIGHT_ANALYTICS_ENABLED를 "false"로 변경합니다.

참고: https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys
