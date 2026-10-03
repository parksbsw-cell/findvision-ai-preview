# FindVision AI 방문 리텐션 통계 연결

설정 전 전체 통계는 비활성화됩니다. 기존 analytics_events는 읽거나 변경하지 않습니다. 방문 통계는 별도 findvision_visits 테이블에 익명 브라우저 ID와 방문 이벤트 시각만 저장합니다.

1. 사용할 Supabase 프로젝트 SQL Editor에서 최신 supabase_setup.sql을 실행합니다. 기존 FindVision 테이블의 데이터는 삭제하지 않습니다.
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

3. 사이트를 새 브라우저 세션으로 열면 방문 이벤트가 1회 기록되는지 확인합니다. 같은 세션의 화면 재실행은 중복 방문으로 세지 않습니다.
4. 같은 브라우저를 다른 한국 날짜에 다시 방문하면 재방문 브라우저와 재방문율에 반영됩니다. 이미지 생성 없이 방문만 해도 집계됩니다.

방문은 Streamlit 브라우저 세션 한 번당 1회로 계산합니다. 화면 재실행과 폼 상호작용은 별도 방문이 아닙니다. 별도 방문 테이블에는 서명된 익명 브라우저 UUID, 임의 방문 이벤트 UUID, 시각만 저장하고 IP·원문·이름·장소·이미지는 저장하지 않습니다. 익명 브라우저 수는 실제 사람 수가 아닙니다. 쿠키 삭제·시크릿 모드·다른 기기는 별도 브라우저로 집계됩니다. 화면의 개인 방문 횟수는 서명된 쿠키에 보관합니다. VISITOR_COOKIE_SECRET을 설정하면 Cloudflare 키 교체와 방문 ID를 분리할 수 있습니다.

누적 집계는 SQL에서 수행하므로 10,000건 제한이 없습니다. RLS를 켜고 anon/authenticated
역할의 읽기·쓰기·집계 함수 실행을 차단합니다. 저장 장애는 사이트 사용을 막지 않으며 전체 통계에 반영되지 않을 수 있습니다. 설정 이전 방문은 소급 복원할 수 없습니다.
끄려면 CLUESIGHT_ANALYTICS_ENABLED를 "false"로 변경합니다.

참고: https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys
