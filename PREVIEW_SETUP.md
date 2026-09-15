# FindVision AI 실험용 복제본

이 브랜치는 기존 공개 앱을 변경하지 않고 새 Streamlit 앱으로 배포하기 위한 복제본입니다. 원본 저장소와 기존 URL에 연결하지 마세요. 새 저장소는 [`parksbsw-cell/findvision-ai-preview`](https://github.com/parksbsw-cell/findvision-ai-preview)입니다.

## 분리 배포

1. 새 저장소에 업그레이드 브랜치 `feat/isolated-streamlit-preview`가 올라왔는지 확인합니다. 원본 코드만 가져온 `main`을 선택하면 새 기능이 보이지 않습니다.
2. Streamlit Community Cloud에서 **새 앱**을 만듭니다.
3. 저장소 `parksbsw-cell/findvision-ai-preview`, 브랜치 `feat/isolated-streamlit-preview`, 실행 파일 `app.py`를 선택합니다.
4. 앱 URL은 기존 앱과 다른 이름(예: `findvision-ai-preview`)으로 지정합니다.
5. 새 앱의 **Settings → Secrets**에 Cloudflare Account ID와 Workers AI 실행 권한이 있는 API Token을 등록하고 저장한 뒤 앱을 재시작합니다. 기존 앱의 설정이나 URL은 바꾸지 않습니다. 두 값이 없으면 화면은 열려도 실제 AI 분석·이미지 생성은 실행되지 않습니다.

```toml
CLOUDFLARE_ACCOUNT_ID = "Cloudflare 대시보드에서 확인한 Account ID"
CLOUDFLARE_API_TOKEN = "Workers AI 실행 권한이 있는 API Token"
```

복제본의 Supabase 통계는 의도적으로 꺼져 있습니다. 개인 사용 횟수는 브라우저 쿠키에만 저장됩니다.

비밀값은 GitHub 파일·커밋·이슈나 이 대화에 붙여 넣지 마세요. 로컬에서는 같은 이름의 환경 변수 또는 로컬 `.streamlit/secrets.toml`을 사용할 수 있으며, 해당 파일은 Git에 올리지 않아야 합니다.

## 새 기능

- 실제 실종 재난문자 원문을 그대로 붙여 넣고, 별도 칸에서 검증된 추가 정보를 작성
- 마지막 목격 위치와 발송 지역 표시(이미지 프롬프트에 장소를 넣지 않음)
- 외투·겉옷을 상의와 다른 레이어로 추출·생성·검수
- 카테고리 옆 브랜드/머리 스타일 표시, 없는 값은 `정보 없음`
- 빠른 생성: `512×768` 이미지 1회 및 검수 1회
- 정밀 생성: `768×1024` 이미지 최대 3회 및 매회 검수
- 이 브라우저에서 완료한 이미지 생성 횟수와 실제 처리 시간 표시

빠른 생성은 재시도를 줄이기 때문에 항상 더 정확한 것은 아닙니다. 속도 개선과 조건 일치 여부는 새 사이트의 실제 테스트 결과로 확인해야 합니다. 생성된 이미지는 실제 인물의 얼굴이나 신원 확인 자료가 아닙니다.

## 로컬 테스트

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
streamlit run app.py
```
