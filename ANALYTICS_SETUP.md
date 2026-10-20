# ClueSight 전체 방문 기록과 분석

영구 방문 통계는 Supabase의 `cluesight_visits` 테이블을 사용합니다. 방문 행에는 익명 브라우저 UUID와 접속 시각만 저장합니다. 재난문자 원문, 이름, 위치, 이미지, IP 주소는 저장하지 않습니다.

1. 사용할 Supabase 프로젝트의 SQL Editor에서 저장소의 `supabase_setup.sql` 전체를 실행합니다. 이 스크립트는 방문 테이블과 전체 누적 집계 RPC를 만들고, 기존 방문 표시 행을 새 테이블로 복사합니다. 이전 행은 삭제하지 않습니다. 생성/방문 지표를 분리해 방문 기록이 생성 수에 섞이지 않게 합니다.

2. Streamlit 앱에서 **Manage app → Settings → Secrets**에 다음을 설정합니다. 기존 Cloudflare 설정은 유지하세요. 실제 값을 GitHub나 채팅에 올리지 마세요.

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SECRET_KEY = "YOUR_SERVER_SECRET_KEY"
ADMIN_PASSWORD = "YOUR_PRIVATE_ADMIN_PASSWORD"
```

서버 전용 `sb_secret_…` 또는 기존 `service_role` 키를 사용하고 anon/publishable 키는 사용하지 않습니다. `SUPABASE_SECRET_KEY`는 브라우저로 전달되지 않습니다.

3. 앱을 연 새 접속 세션마다 방문 행을 하나 기록합니다. 같은 세션의 화면 재실행은 같은 이벤트 ID로 중복 저장되지 않습니다. 브라우저를 다시 열면 재방문으로 기록됩니다. 날짜 필터나 REST 페이지 제한 없이 DB에서 전체 행을 집계하므로 누적값은 날짜가 바뀌어도 초기화되지 않습니다.

4. 사이트 상단에서 누적 방문자, 전체 방문 횟수, 재방문자, 리텐션을 확인합니다. Supabase가 설정되기 전에는 기존처럼 서버 임시 저장소의 값을 표시하며, 재배포나 서버 재시작 후에는 그 값이 초기화될 수 있습니다. SQL과 Secrets 설정이 끝나면 앱이 이전 임시 방문 기록(남아 있는 경우)을 영구 DB로 한 번 복사하고, 이후 기록은 Supabase에 저장합니다. DB 오류가 있으면 현재 표시값과 오류 안내를 함께 보여줍니다.

누적 방문자와 재방문자는 익명 브라우저 UUID 기준이며 실제 사람 수와 다를 수 있습니다. 쿠키 삭제, 시크릿 모드, 다른 브라우저·기기는 각각 별도 브라우저로 계산됩니다. 리텐션은 전체 누적 방문 중 2회 이상 방문한 브라우저의 비율입니다.

