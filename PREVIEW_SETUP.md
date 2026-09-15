# FindVision AI 실험용 복제본

이 브랜치는 기존 공개 앱(`main`의 `app.py`)을 변경하지 않고 새 Streamlit 앱으로 배포하기 위한 복제본입니다. 기존 URL에 연결하지 마세요.

## 분리 배포

1. GitHub에서 `feat/isolated-streamlit-preview` 브랜치를 확인합니다.
2. Streamlit Community Cloud에서 **새 앱**을 만듭니다.
3. 저장소 `rnwkdns11-collab/findvision-ai`, 브랜치 `feat/isolated-streamlit-preview`, 실행 파일 `app.py`를 선택합니다.
4. 앱 URL은 기존 앱과 다른 이름(예: `findvision-ai-preview`)으로 지정합니다.
5. 새 앱의 Secrets에 Cloudflare Account ID와 API Token을 따로 등록합니다. 기존 앱의 설정이나 URL은 바꾸지 않습니다.

```toml
CLOUDFLARE_ACCOUNT_ID = "새 앱에서 사용할 Account ID"
CLOUDFLARE_API_TOKEN = "새 앱에서 사용할 API Token"
```

복제본의 Supabase 통계는 의도적으로 꺼져 있습니다. 개인 사용 횟수는 브라우저 쿠키에만 저장됩니다.

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
