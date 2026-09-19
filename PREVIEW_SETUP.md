# ClueSight / FindVision AI — 배포 및 운영 확인

이 저장소 `parksbsw-cell/findvision-ai-preview`는 기존 원본 저장소 `rnwkdns11-collab/findvision-ai`와 별개의 복제본입니다. 두 저장소가 같은 실제 사이트에 배포되는 것으로 추측하지 마세요.

## 현재 코드

- 개선된 인상착의 추출 코드가 `main`에 병합되었습니다. `feat/isolated-streamlit-preview`에도 동일한 기능 코드가 있습니다.
- 헤어스타일(투블럭·버섯머리·장발 등), 명시된 옷 브랜드, 체형, 마지막 목격 장소, 재난문자 발송 지역의 추출을 개선했습니다.
- 사용 횟수는 **현재 브라우저에 저장된 완료 횟수**이며 전체 이용자 수를 뜻하지 않습니다.
- 빠른 생성은 512×768 이미지 1회와 검수 1회, 정밀 생성은 768×1024 이미지 최대 3회와 매회 검수입니다. 빠른 모드는 정확도나 응답시간 개선을 보장하지 않으므로 실측이 필요합니다.
- 하단 `다시 생성하기` 버튼은 현재 입력을 유지하여 재생성합니다.
- **Supabase 서버 통계는 이 복제본에서 비활성화되어 있습니다.** 관리자 지표가 실제 수치를 표시하려면 사용자 동의/운영 범위와 별도 Supabase 설정을 검토한 뒤 코드를 활성화해야 합니다. 현재 이를 완료했다고 표시하지 마세요.
- 생성 이미지와 자동 검수 점수는 참고 자료입니다. 실제 인물의 얼굴·신원이나 검증된 정확도를 의미하지 않습니다.

## Streamlit Community Cloud에서 별도 앱으로 배포

1. `https://share.streamlit.io`에 앱 배포 권한이 있는 계정으로 로그인합니다.
2. 기존 앱을 바꾸지 않고 시험하려면 Create app에서 저장소 `parksbsw-cell/findvision-ai-preview`, 브랜치 `main`, 파일 `app.py`로 **새 앱**을 생성합니다.
3. 해당 앱 Settings → Secrets에 `CLOUDFLARE_ACCOUNT_ID`와 Workers AI 실행 권한이 있는 `CLOUDFLARE_API_TOKEN`을 직접 입력합니다. 값은 GitHub/채팅/이 문서에 기록하지 마세요.
4. 배포 로그에서 의존성 설치와 앱 시작 성공을 확인하고 테스트용 허구 재난문자로 빠른/정밀 생성, 필드 추출, 재생성, 실패 안내를 검증합니다.
5. 실제 운영 앱을 바꾸려면 **운영 앱의 정확한 URL, 연결된 GitHub 저장소·브랜치·실행 파일, 해당 계정의 관리 권한**을 확인해야 합니다. GitHub에 코드를 올렸다는 이유만으로 배포 완료라 주장하지 마세요. 원본 저장소를 사용하는 운영 앱이라면 이 복제본의 업데이트는 자동 반영되지 않습니다.

## 로컬 / 자동 검증

```bash
pip install -r requirements-dev.txt
python -m py_compile app.py preview_logic.py
ruff check .
pytest -q
streamlit run app.py
```

모든 기능이 실제로 동작하는지 최종 확인하려면 Cloudflare API를 사용한 실측 시험이 별도로 필요합니다.
