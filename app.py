import base64
import hmac
import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
import streamlit as st
from streamlit_cookies_controller import CookieController

from preview_logic import (
    BRANDS,
    analysis_message,
    category_text,
    enhance_features_from_text,
    image_mime,
    known_appearance_count,
    missing_recommended,
    safe_count,
    verification_result,
    visual_facts,
)

# =========================================================
# 기본 설정
# =========================================================

st.set_page_config(
    page_title="ClueSight",
    page_icon="🔎",
    layout="wide",
)

cookie_controller = CookieController()

TEXT_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"
IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
VISION_MODEL = "@cf/moondream/moondream3.1-9B-A2B"

MAX_ATTEMPTS = 3
FAST_ATTEMPTS = 1
FAST_WIDTH = 512
FAST_HEIGHT = 768
DETAILED_WIDTH = 768
DETAILED_HEIGHT = 1024

FIELDS = [
    "name",
    "gender",
    "age",
    "height",
    "weight",
    "body_type",
    "nationality",
    "skin_tone",
    "hair_color",
    "hair_length",
    "hair_texture",
    "hair_style",
    "top",
    "top_brand",
    "outerwear",
    "outerwear_brand",
    "bottom",
    "bottom_brand",
    "shoes",
    "shoes_brand",
    "hat_type",
    "hat_color",
    "hat_brand",
    "glasses",
    "facial_hair",
    "accessories",
    "special_features",
    "image_prompt_en",
    "verification_requirements_en",
    "ambiguity_notes",
    "last_seen_location",
    "alert_area",
]

LABELS = {
    "name": "이름",
    "gender": "성별",
    "age": "나이",
    "height": "키",
    "weight": "몸무게",
    "body_type": "체형",
    "nationality": "국적",
    "skin_tone": "피부톤",
    "hair_color": "머리색",
    "hair_length": "머리 길이",
    "hair_texture": "머리 형태",
    "hair_style": "머리 스타일",
    "top": "상의",
    "top_brand": "상의 브랜드",
    "outerwear": "외투·겉옷",
    "outerwear_brand": "겉옷 브랜드",
    "bottom": "하의",
    "bottom_brand": "하의 브랜드",
    "shoes": "신발",
    "shoes_brand": "신발 브랜드",
    "hat_type": "모자 종류",
    "hat_color": "모자 색상",
    "hat_brand": "모자 브랜드",
    "glasses": "안경",
    "facial_hair": "수염",
    "accessories": "소지품·액세서리",
    "special_features": "기타 특징",
    "last_seen_location": "마지막 목격 위치",
    "alert_area": "재난문자 발송 지역",
}


# =========================================================
# Cloudflare API
# =========================================================


def get_secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, "")).strip()


def cf_url(model: str) -> str:
    account_id = get_secret("CLOUDFLARE_ACCOUNT_ID")
    if not account_id:
        raise RuntimeError("Cloudflare Account ID가 설정되어 있지 않습니다.")
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"


def auth_header() -> dict:
    token = get_secret("CLOUDFLARE_API_TOKEN")
    if not token:
        raise RuntimeError("Cloudflare API Token이 설정되어 있지 않습니다.")
    return {"Authorization": f"Bearer {token}"}


def json_headers() -> dict:
    headers = auth_header()
    headers["Content-Type"] = "application/json"
    return headers


def cloudflare_json_request(model: str, payload: dict, timeout: int = 120) -> Any:
    response = requests.post(
        cf_url(model),
        headers=json_headers(),
        json=payload,
        timeout=timeout,
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Cloudflare 응답을 읽지 못했습니다. HTTP {response.status_code}"
        ) from exc

    if not response.ok or not data.get("success", False):
        flagged = "flagged" in json.dumps(data).lower()
        if flagged:
            raise RuntimeError("이미지 제공자의 안전 검사로 생성이 중단되었습니다. 자동 재시도하지 않습니다.")
        raise RuntimeError(f"AI 제공자 요청 실패 (HTTP {response.status_code}). 잠시 후 다시 시도해 주세요.")

    return data.get("result")


def cloudflare_multipart_request(model: str, fields: dict, timeout: int = 180) -> Any:
    # requests의 files 형식을 사용하면 multipart/form-data boundary가 자동 생성된다.
    multipart = {key: (None, str(value)) for key, value in fields.items()}

    response = requests.post(
        cf_url(model),
        headers=auth_header(),
        files=multipart,
        timeout=timeout,
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Cloudflare 이미지 응답을 읽지 못했습니다. HTTP {response.status_code}"
        ) from exc

    if not response.ok or not data.get("success", False):
        flagged = "flagged" in json.dumps(data).lower()
        if flagged:
            raise RuntimeError("이미지 제공자의 안전 검사로 생성이 중단되었습니다. 자동 재시도하지 않습니다.")
        raise RuntimeError(f"AI 제공자 요청 실패 (HTTP {response.status_code}). 잠시 후 다시 시도해 주세요.")

    return data.get("result")


# =========================================================
# 재난문자 분석
# =========================================================


def extract_features(original: str) -> dict:
    schema = {
        "type": "object",
        "properties": {key: {"type": "string"} for key in FIELDS},
        "required": FIELDS,
        "additionalProperties": False,
    }

    system_prompt = """
너는 실종 재난문자의 인상착의 사실 추출기다.

절대 원칙:
- 원문에 실제로 있는 정보만 사용한다.
- 없는 정보는 빈 문자열("")로 둔다.
- 모호한 정보를 추측하지 않는다.
- 이름만 보고 국적, 피부톤, 머리 특징을 추측하지 않는다.
- 옷·모자·신발 브랜드, 머리 스타일은 명시된 경우에만 기입한다. 없으면 빈 문자열로 둔다.
- last_seen_location은 마지막 목격 장소, alert_area는 재난문자 발송 지역이다. 장소를 외형으로 해석하지 않는다.

한국어 필드 작성 규칙:
1. "검은색 모자" -> hat_type="모자(종류 불명)", hat_color="검은색"
2. "회색 캡모자" -> hat_type="캡모자", hat_color="회색"
3. "검은색 바지" -> bottom="검은색 바지". 긴바지/반바지를 추측하지 않는다.
4. 피부톤, 곱슬/직모, 수염, 안경 등은 명시된 경우만 적는다.
5. ambiguity_notes에는 구체적으로 정할 수 없는 부분을 한국어로 적는다.
6. 티셔츠·셔츠·니트는 top, 자켓·점퍼·코트·바람막이·후드집업·패딩·외투는 outerwear로 분리한다.
7. 체형은 비만, 통통한 편, 마른 편, 저체중 등 명시된 경우 body_type에 적는다.
8. 겉옷이 있더라도 top을 삭제하지 않는다. 단, 겉옷 안의 상의가 명시되지 않았으면 top은 비운다.
9. 소지품과 액세서리는 accessories에 가능한 한 빠짐없이 적는다.

image_prompt_en 규칙:
- 반드시 자연스럽고 정확한 영어로 작성한다.
- 원문에 있는 사실만 포함한다.
- 현대의 일상복 기준으로 표현한다.
- 실제 얼굴 생김새를 창작하지 않는다.
- 국적이 없는 경우 특정 국적을 추가하지 않는다.
- 겉옷은 상의 위에 겹쳐 입는 레이어로 명확하게 기술한다.
- 브랜드 이름은 명시된 경우 의류 디자인 설명에만 사용하고 로고·문자를 생성하라고 요구하지 않는다.

verification_requirements_en 규칙:
- 이미지에서 반드시 확인해야 할 명시된 인상착의만 영어로 적는다.
- 세미콜론(;)으로 구분한다.
- 예: "gray baseball cap; red short-sleeve T-shirt;
  black long pants; black Crocs; short black curly hair"
- 원문에 없는 특징은 절대로 추가하지 않는다.
- 겉옷이 명시된 경우에만 색·종류를 포함한다.
- 닫힌 겉옷에 가려진 안쪽 상의는 시각 검수 필수 조건에 넣지 않는다.
- 위치·이름은 이미지 검수 조건에 넣지 않는다.
""".strip()

    result = cloudflare_json_request(
        TEXT_MODEL,
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": analysis_message(original),
                },
            ],
            "temperature": 0.0,
            "max_tokens": 1800,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": schema,
            },
        },
    )

    parsed = result.get("response", result) if isinstance(result, dict) else result

    if isinstance(parsed, str):
        parsed = json.loads(parsed)

    if not isinstance(parsed, dict):
        raise RuntimeError("AI 분석 결과가 올바른 형식이 아닙니다.")

    features = {key: str(parsed.get(key, "") or "").strip() for key in FIELDS}
    features = enhance_features_from_text(features, original, "")
    return sync_prompt_text_from_structured_features(features)


def phrase_to_prompt_en(value: str) -> str:
    text = str(value or "").strip()
    replacements = [
        ("투블럭컷", "two-block haircut"), ("투블럭", "two-block haircut with short sides and longer top"),
        ("히피펌", "tight curly perm"), ("가르마펌", "side-parted perm"),
        ("리프컷", "layered medium-length leaf haircut"), ("댄디컷", "neat short haircut with fringe"),
        ("포마드", "slicked-back pompadour"), ("울프컷", "layered wolf cut"),
        ("스포츠머리", "short athletic haircut"), ("반삭머리", "buzz cut"),
        ("반삭", "buzz cut"), ("삭발", "shaved head"), ("숏컷", "short haircut"),
        ("단발머리", "bob haircut"), ("단발", "bob haircut"), ("보브컷", "bob haircut"),
        ("장발", "long hair"), ("긴머리", "long hair"), ("포니테일", "ponytail"),
        ("묶은머리", "tied-back hair"), ("땋은머리", "braided hair"),
        ("파마머리", "permed hair"), ("파마", "permed hair"),
        ("고도 비만", "very heavy build"), ("고도비만", "very heavy build"),
        ("보통 체형", "average build"), ("남성", "male"), ("여성", "female"),
        ("청바지", "jeans"), ("초록색", "green"), ("노란색", "yellow"),
        ("베이지색", "beige"), ("갈색", "brown"), ("분홍색", "pink"),
        ("보라색", "purple"), ("주황색", "orange"),
        ("후드집업", "zip-up hoodie"), ("후드티", "hoodie"), ("맨투맨", "sweatshirt"),
        ("티셔츠", "T-shirt"), ("셔츠", "shirt"), ("니트", "knit sweater"),
        ("바람막이", "windbreaker"), ("패딩", "puffer jacket"),
        ("점퍼", "jacket"), ("자켓", "jacket"), ("재킷", "jacket"),
        ("코트", "coat"), ("외투", "coat"), ("겉옷", "outerwear"),
        ("슬랙스", "slacks"), ("치마", "skirt"), ("레깅스", "leggings"),
        ("부츠", "boots"), ("구두", "dress shoes"), ("샌들", "sandals"),
        ("단화", "flat shoes"), ("백팩", "backpack"),
        ("검은색", "black"),
        ("검정색", "black"),
        ("흰색", "white"),
        ("하얀색", "white"),
        ("회색", "gray"),
        ("빨간색", "red"),
        ("붉은색", "red"),
        ("파란색", "blue"),
        ("남색", "navy"),
        ("밝은 편", "light skin tone"),
        ("어두운 편", "dark skin tone"),
        ("통통한 편", "stocky build"),
        ("뚱뚱한 편", "heavy build"),
        ("건장한 편", "sturdy build"),
        ("마른 편", "thin build"),
        ("저체중", "underweight build"),
        ("비만", "obese build"),
        ("약간 짧음", "slightly short"),
        ("짧음", "short"),
        ("반팔티", "short-sleeve T-shirt"),
        ("반팔 상의", "short-sleeve top"),
        ("반팔", "short-sleeve"),
        ("긴팔티", "long-sleeve T-shirt"),
        ("상의", "top"),
        ("로고있는", "with a logo"),
        ("로고 있는", "with a logo"),
        ("로고없는", "without a logo"),
        ("로고 없는", "without a logo"),
        ("반바지", "shorts"),
        ("긴바지", "long pants"),
        ("바지", "pants"),
        ("크록스", "Crocs"),
        ("슬리퍼", "slippers"),
        ("운동화", "sneakers"),
        ("모자(종류 불명)", "hat of unspecified type"),
        ("캡모자", "baseball cap"),
        ("모자", "hat"),
        ("버섯머리", "mushroom haircut"),
        ("직모", "straight hair"),
        ("곱슬", "curly hair"),
        ("안경", "glasses"),
        ("없음", "none"),
        ("작은가방", "small bag"),
        ("가방", "bag"),
        ("휴대폰", "phone"),
        ("지갑", "wallet"),
        ("우산", "umbrella"),
        ("목걸이", "necklace"),
        ("팔찌", "bracelet"),
        ("시계", "watch"),
    ]
    for source, target in replacements:
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def sync_prompt_text_from_structured_features(features: dict) -> dict:
    """Rebuild from structured appearance only; discard free-form model prose."""
    parts = []
    requirements = []
    for key, value in visual_facts(features).items():
        if key.endswith("_brand") or key == "nationality":
            continue
        # Brands remain in the analysis display. Logos are not verification criteria.
        for brand in BRANDS:
            if brand.lower() not in {"crocs", "크록스"}:
                value = re.sub(re.escape(brand), "", value, flags=re.I)
        value = value.replace("크록스", "clogs").replace("Crocs", "clogs")
        value = re.sub(r"로고\s*(있는|없는)|[()]", "", value).strip()
        part = f"{key.replace('_', ' ')}: {phrase_to_prompt_en(value)}"
        parts.append(part)
        if key not in {"height", "weight", "age"}:
            requirements.append(part)
    features["image_prompt_en"] = "; ".join(parts)
    features["verification_requirements_en"] = "; ".join(requirements)
    return features


def _merge_prompt_lines(*parts: str) -> str:
    return "\n".join(part for part in parts if str(part or "").strip())


# =========================================================
# 기본 인물 설정 / 상세도 검사
# =========================================================


def get_origin(features: dict) -> tuple[str, str]:
    nationality = features.get("nationality", "").strip()
    if nationality:
        return nationality, nationality
    return "국적 정보 없음", ""


def get_known_appearance_count(features: dict) -> int:
    return known_appearance_count(features)


def get_missing_recommended(features: dict) -> list[str]:
    return missing_recommended(features)


# =========================================================
# 이미지 생성
# =========================================================


def build_generation_prompt(
    features: dict,
    origin_en: str,
    correction: str = "",
) -> str:

    features = sync_prompt_text_from_structured_features(dict(features))
    description = features["image_prompt_en"]
    if not description:
        raise RuntimeError("이미지 생성에 필요한 인상착의 정보가 없습니다.")
    layers = ("Wear the stated outerwear over the inner top. A closed outer layer may hide the top."
              if features.get("outerwear") else "No outerwear is specified; do not add a coat or jacket.")
    prompt = (
        "Create one photorealistic full-body appearance reference of a fictional person. "
        "This is an illustration of described clothing and build, not an identified person's face. "
        "Standing front view, head and feet visible, plain light background, contemporary clothing. "
        "Match only the stated appearance facts; unspecified details are illustrative. "
        "No text, logos or watermark. " + layers + "\n" + description
    )
    if correction:
        prompt += "\nCorrect these visible mismatches only: " + correction[:800]
    return prompt


def generate_image(prompt: str, width: int, height: int) -> tuple[bytes, str, str]:
    # FLUX.2 Klein은 REST API에서 multipart/form-data 사용
    result = cloudflare_multipart_request(
        IMAGE_MODEL,
        {
            "prompt": prompt,
            "width": width,
            "height": height,
            # 값이 높을수록 프롬프트를 더 강하게 따르도록 유도
            "guidance": 4.0,
        },
    )

    if not isinstance(result, dict) or not result.get("image"):
        raise RuntimeError("이미지 생성 결과를 받지 못했습니다.")

    image_b64 = result["image"]
    image_bytes = base64.b64decode(image_b64)
    return image_bytes, image_b64, image_mime(image_bytes)


# =========================================================
# Vision AI 검수
# =========================================================


def extract_text_from_result(result: Any, depth: int = 0) -> str:
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        for key in ("answer", "response", "result", "text", "caption"):
            value = result.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, dict) and depth < 4:
                return extract_text_from_result(value, depth + 1)

    return json.dumps(result, ensure_ascii=False)


def moondream_query(image_b64: str, mime_type: str, question: str) -> str:
    safe_mime = mime_type if mime_type.startswith("image/") else "image/jpeg"
    data_uri = f"data:{safe_mime};base64,{image_b64}"

    result = cloudflare_json_request(
        VISION_MODEL,
        {
            "task": "query",
            "image": data_uri,
            "question": question,
            "reasoning": False,
            "temperature": 0.0,
            "max_tokens": 900,
            "stream": False,
        },
    )

    return extract_text_from_result(result)


def parse_json_loose(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    return {}


def verify_image(image_b64: str, mime_type: str, features: dict) -> dict:
    requirements = features.get("verification_requirements_en", "").strip()
    structured_facts = json.dumps(visual_facts(features), ensure_ascii=False)
    has_outerwear = bool(str(features.get("outerwear", "") or "").strip())
    outerwear_check = (
        "The stated outerwear must be visibly worn over the inner top, not omitted or merged into it.\n"
        "If outerwear is closed, do not demand that its covered inner top be fully visible."
        if has_outerwear
        else "No outerwear was specified; do not require a coat or jacket."
    )
    outerwear_rejection = (
        "- required outerwear type/color/layer is wrong or missing"
        if has_outerwear
        else ""
    )

    question = f"""
Carefully verify this generated full-body reference image.

EXPLICIT REQUIRED FACTS:
{requirements}

USER-SUPPLIED STRUCTURED APPEARANCE FACTS (source of truth):
{structured_facts}

{outerwear_check}
Never verify a brand by assuming a logo must appear.
Name and location are context, not visual appearance requirements.

Only evaluate facts explicitly listed above.
Do not penalize unspecified face details.

Reject the image if:
- any required clothing color is wrong
- any required clothing type is wrong
{outerwear_rejection}
- required shoes are wrong
- required hat type/color is wrong
- specified hair or skin characteristics are wrong
- the full body is not visible
- traditional, historical, ceremonial or fantasy clothing appears without being required
- any text, calligraphy, letters, numbers, logo, sign, poster or watermark appears
- the image is anime/cartoon/illustration instead of a realistic reference photograph

Return JSON ONLY:
{{
  "score": 0,
  "pass": false,
  "missing": [],
  "wrong": [],
  "has_text": false,
  "feedback_en": ""
}}

score must be an integer from 0 to 100. Set pass=true only for score >= 80
with no missing or wrong visible requirements.
feedback_en must tell the image generator exactly what to correct.
""".strip()

    raw = moondream_query(image_b64, mime_type, question)
    parsed = parse_json_loose(raw)

    if not parsed:
        return {
            "score": 0,
            "available": False,
            "pass": False,
            "missing": [],
            "wrong": ["검수 결과를 읽지 못함"],
            "has_text": False,
            "feedback_en": (
                "Regenerate as a photorealistic contemporary full-body reference photo. "
                "Follow every explicit requirement exactly and include absolutely no text."
            ),
            "raw": raw,
        }

    return verification_result(parsed, raw)


# =========================================================
# 익명 사용 통계 / Supabase
# =========================================================


def analytics_enabled() -> bool:
    # Explicit opt-in; the dedicated ClueSight table isolates legacy metrics.
    return (get_secret("CLUESIGHT_ANALYTICS_ENABLED").lower() == "true"
            and bool(get_secret("SUPABASE_URL")) and bool(supabase_key()))


def supabase_key() -> str:
    return get_secret("SUPABASE_SECRET_KEY")


def get_anonymous_user_id() -> str:
    """
    브라우저 쿠키에 익명 UUID를 저장한다.
    이름, 재난문자 원문, IP 주소 등은 통계 DB에 저장하지 않는다.
    """
    if "findvision_uid" in st.session_state:
        return st.session_state["findvision_uid"]

    try:
        saved = cookie_controller.get("findvision_uid")
    except Exception:
        saved = None

    try:
        saved = str(uuid.UUID(str(saved))) if saved else None
    except ValueError:
        saved = None
    if saved:
        user_id = str(saved)
    else:
        user_id = str(uuid.uuid4())
        try:
            cookie_controller.set("findvision_uid", user_id, max_age=365 * 24 * 60 * 60)
        except Exception:
            pass

    st.session_state["findvision_uid"] = user_id
    return user_id


def supabase_headers() -> dict:
    key = supabase_key()
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def log_analytics_event(user_id, event_type, verification_pass=None,
                        verification_score=None, attempts=None, event_id=None,
                        mode=None, first_image_seconds=None, total_seconds=None) -> bool:
    if not analytics_enabled():
        return False
    payload = dict(event_id=event_id or str(uuid.uuid4()), user_id=user_id,
                   event_type=event_type, verification_pass=verification_pass,
                   verification_score=verification_score, attempts=attempts,
                   mode=mode, first_image_seconds=first_image_seconds, total_seconds=total_seconds)
    try:
        response = requests.post(
            get_secret("SUPABASE_URL").rstrip("/") + "/rest/v1/cluesight_events",
            headers={**supabase_headers(), "Prefer": "resolution=ignore-duplicates,return=minimal"},
            params={"on_conflict": "event_id"}, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except Exception:
        return False


def fetch_analytics_summary() -> dict:
    response = requests.post(
        get_secret("SUPABASE_URL").rstrip("/") + "/rest/v1/rpc/cluesight_analytics_summary",
        headers=supabase_headers(), json={}, timeout=10)
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or "total_generations" not in result:
        raise ValueError("Invalid analytics summary")
    return result


def parse_created_at(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def calculate_analytics(rows: list) -> dict:
    generations = [row for row in rows if row.get("event_type") == "image_generated"]

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    all_users = set()
    weekly_users = set()
    usage_dates = {}
    weekly_usage_dates = {}

    for row in generations:
        user_id = row.get("user_id")
        created_at = parse_created_at(row.get("created_at", ""))

        if not user_id or not created_at:
            continue

        all_users.add(user_id)
        usage_dates.setdefault(user_id, set()).add(created_at.date())

        if created_at >= seven_days_ago:
            weekly_users.add(user_id)
            weekly_usage_dates.setdefault(user_id, set()).add(created_at.date())

    returning_users = {user_id for user_id, dates in usage_dates.items() if len(dates) >= 2}

    weekly_returning_users = {
        user_id for user_id, dates in weekly_usage_dates.items() if len(dates) >= 2
    }

    verification_rows = [row for row in generations if row.get("verification_pass") is not None]

    passed = sum(1 for row in verification_rows if row.get("verification_pass") is True)

    pass_rate = 100.0 * passed / len(verification_rows) if verification_rows else 0.0

    attempts_values = [
        int(row["attempts"]) for row in generations if row.get("attempts") is not None
    ]

    avg_attempts = sum(attempts_values) / len(attempts_values) if attempts_values else 0.0

    return {
        "total_users": len(all_users),
        "weekly_active_users": len(weekly_users),
        "returning_users": len(returning_users),
        "weekly_returning_users": len(weekly_returning_users),
        "total_generations": len(generations),
        "verification_pass_rate": pass_rate,
        "avg_attempts": avg_attempts,
    }


def show_admin_analytics() -> None:
    st.subheader("📊 ClueSight 서비스 사용 지표")

    if not analytics_enabled():
        st.info("전체 통계가 연결되지 않았습니다. 설정 전 사용량을 전체 사용자 수로 표시하지 않습니다.")
        return

    admin_password = get_secret("ADMIN_PASSWORD")
    if not admin_password:
        st.warning("ADMIN_PASSWORD가 설정되어 있지 않습니다.")
        return

    entered = st.text_input(
        "관리자 비밀번호",
        type="password",
        key="analytics_admin_password",
    )

    if not hmac.compare_digest(entered.encode("utf-8"), admin_password.encode("utf-8")):
        if entered:
            st.error("비밀번호가 맞지 않습니다.")
        return

    try:
        metrics = fetch_analytics_summary()
    except Exception:
        st.error("통계 연결을 확인해 주세요. 현재 집계값을 불러오지 못했습니다.")
        return

    a, b, c = st.columns(3)
    a.metric("누적 생성 브라우저", f"{metrics['total_users']}개")
    b.metric(
        "최근 7일 생성 브라우저",
        f"{metrics['weekly_active_users']}개",
        help="최근 7일 안에 이미지 생성을 1회 이상 완료한 익명 브라우저",
    )
    c.metric(
        "재방문 브라우저",
        f"{metrics['returning_users']}개",
        help="서로 다른 날짜에 이미지 생성을 2회 이상 완료한 익명 브라우저",
    )

    d, e, f = st.columns(3)
    d.metric(
        "최근 7일 재방문 브라우저",
        f"{metrics['weekly_returning_users']}개",
        help="최근 7일 동안 서로 다른 날짜에 2회 이상 사용한 익명 브라우저",
    )
    e.metric("총 이미지 생성", f"{metrics['total_generations']}회")
    f.metric(
        "자동 검수 통과율",
        f"{metrics['verification_pass_rate']:.1f}%",
    )

    st.caption(f"평균 이미지 생성 시도 횟수: {metrics['avg_attempts']:.2f}회")
    st.caption("익명 브라우저 기준이며 실제 사람 수와 다릅니다. 재방문 날짜는 한국 시간 기준입니다. 원문·이미지·이름·위치는 통계 DB에 저장하지 않습니다.")


def get_my_usage_count() -> int:
    session_count = safe_count(st.session_state.get("preview_usage_count"))
    try:
        cookie_count = safe_count(cookie_controller.get("findvision_preview_usage_count"))
    except Exception:
        cookie_count = 0
    count = max(session_count, cookie_count)
    st.session_state["preview_usage_count"] = count
    return count


def record_my_use() -> int:
    count = min(get_my_usage_count() + 1, 1_000_000)
    st.session_state["preview_usage_count"] = count
    try:
        cookie_controller.set("findvision_preview_usage_count", str(count), max_age=365 * 24 * 60 * 60)
    except Exception:
        pass
    return count


# =========================================================
# UI
# =========================================================

st.title("🔎 ClueSight")
st.caption("인상착의를 이해하는 AI 참고 이미지 · 버전 2026.09.20")
missing_cloudflare_settings = [
    name
    for name in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN")
    if not get_secret(name)
]
if missing_cloudflare_settings:
    st.warning(
        "실제 AI 분석·이미지 생성을 사용하려면 앱의 Streamlit Secrets에 "
        + ", ".join(missing_cloudflare_settings)
        + "을(를) 등록해야 합니다. GitHub 저장소에 API 키를 올리지 마세요. "
        "설정 방법은 PREVIEW_SETUP.md를 확인하세요."
    )
usage_metric = st.empty()
usage_metric.metric("내가 이미지 생성에 사용한 횟수", f"{get_my_usage_count()}회")
st.caption("이 브라우저에 저장된 완료 횟수입니다. 다른 기기에서는 별도로 계산됩니다.")

st.caption(
    "상세 실종 재난문자를 AI가 분석하고, 인상착의를 반영한 "
    "현대적인 전신 참고 이미지를 생성한 뒤 Vision AI가 다시 검수합니다."
)

st.warning(
    "생성 이미지는 실제 실종자의 얼굴을 복원한 사진이 아닙니다. "
    "재난문자에 적힌 인상착의를 이해하기 위한 참고 자료입니다."
)


with st.expander("🔒 팀 관리자용 사용 통계", expanded=False):
    show_admin_analytics()

with st.expander("📌 권장 상세 재난문자 기준", expanded=True):
    st.markdown(
        """
가능하면 다음 정보를 포함해 주세요.

- 성별 / 나이 / 키 / 몸무게
- 체형(비만 / 저체중 / 통통한 편 / 마른 편 등)
- 피부톤
- 머리색 / 머리 길이 / 곱슬·직모 등 머리 형태
- 상의 색상과 종류
- 외투·겉옷 색상과 종류
- 하의 색상과 종류
- 신발 색상과 종류
- 모자 색상과 정확한 종류
- 브랜드나 머리 스타일(실제 문자에 적힌 경우만)
- 마지막 목격 위치와 재난문자 발송 지역
- 안경 / 수염 / 소지품 등 기타 특징

**없는 정보는 AI가 임의로 사실처럼 확정하지 않습니다.**
        """
    )

message = st.text_area(
    "실종 재난문자 원문 — 그대로 붙여 넣기",
    value="",
    placeholder="받은 실종 재난문자 원문을 수정하지 않고 붙여 넣으세요.",
    height=170,
    max_chars=1500,
)

mode = st.radio(
    "생성 방식",
    ["빠른 생성", "정밀 생성"],
    horizontal=True,
    help="빠른 생성은 작은 이미지 1회+검수 1회, 정밀 생성은 큰 이미지로 최대 3회 재시도합니다.",
)


primary_clicked = st.button(
    "AI 분석 및 참고 이미지 생성",
    type="primary",
    use_container_width=True,
)
run_requested = primary_clicked or st.session_state.pop("regenerate_requested", False)

if run_requested:
    if not message.strip():
        st.warning("실종 재난문자를 입력해 주세요.")
    else:
        try:
            started_at = time.perf_counter()
            with st.spinner("인상착의를 분석하고 있습니다..."):
                features = extract_features(message.strip())
            if get_known_appearance_count(features) < 3:
                st.warning("인상착의 정보가 부족합니다. 옷·머리·신발 등 확인된 특징을 추가해 주세요.")
            else:
                st.session_state["last_analysis"] = features
                best = None
                correction = ""
                attempts_allowed = FAST_ATTEMPTS if mode == "빠른 생성" else MAX_ATTEMPTS
                width = FAST_WIDTH if mode == "빠른 생성" else DETAILED_WIDTH
                height = FAST_HEIGHT if mode == "빠른 생성" else DETAILED_HEIGHT
                first_image_seconds = None
                attempts_completed = 0
                interrupted = False
                status = st.empty()
                interim = st.empty()
                for attempt in range(1, attempts_allowed + 1):
                    status.info(f"{attempt}차 이미지 생성 중...")
                    prompt = build_generation_prompt(features, "", correction)
                    try:
                        image_bytes, image_b64, mime_type = generate_image(prompt, width, height)
                    except Exception:
                        if best is None:
                            raise
                        interrupted = True
                        break
                    attempts_completed += 1
                    if first_image_seconds is None:
                        first_image_seconds = time.perf_counter() - started_at
                    interim.image(image_bytes, caption="생성 완료 · 자동 검수 중", use_container_width=True)
                    status.info(f"{attempt}차 이미지 검수 중...")
                    try:
                        verdict = verify_image(image_b64, mime_type, features)
                    except Exception:
                        verdict = {"score": 0, "pass": False, "missing": [], "wrong": [],
                                   "feedback_en": "", "available": False}
                    candidate = {"attempt": attempt, "image": image_bytes, "verification": verdict}
                    if best is None or (verdict["pass"], verdict["available"], verdict["score"]) > (
                        best["verification"]["pass"], best["verification"]["available"], best["verification"]["score"]
                    ):
                        best = candidate
                    if verdict["pass"] or not verdict["available"]:
                        break
                    correction = verdict["feedback_en"]
                status.empty()
                interim.empty()
                total_seconds = time.perf_counter() - started_at
                event_id = str(uuid.uuid4())
                result = dict(best=best, features=features, message=message,
                              mode=mode, width=width, height=height, attempts=attempts_completed,
                              first_image_seconds=first_image_seconds, total_seconds=total_seconds,
                              interrupted=interrupted, event_id=event_id)
                st.session_state["last_result"] = result
                st.session_state.pop("generation_error", None)
                usage_metric.metric("내가 이미지 생성에 사용한 횟수", f"{record_my_use()}회")
                verdict = best["verification"]
                result["analytics_saved"] = log_analytics_event(
                    get_anonymous_user_id(), "image_generated",
                    verification_pass=verdict["pass"] if verdict["available"] else None,
                    verification_score=verdict["score"] if verdict["available"] else None,
                    attempts=attempts_completed, event_id=event_id, mode=mode,
                    first_image_seconds=first_image_seconds, total_seconds=total_seconds)
        except Exception as exc:
            # Never show request URLs, headers, provider payloads or credentials.
            error = str(exc)
            if "안전 검사" in error:
                st.session_state["generation_error"] = error
            else:
                st.session_state["generation_error"] = "생성을 완료하지 못했습니다. 연결 상태를 확인한 뒤 다시 시도해 주세요."

if st.session_state.get("generation_error"):
    st.error(st.session_state["generation_error"])

result = st.session_state.get("last_result")
features = result["features"] if result else st.session_state.get("last_analysis")
if features:
    st.subheader("1. 분석된 인상착의")
    c1, c2 = st.columns(2)
    display_keys = ["gender", "age", "height", "weight", "body_type", "skin_tone",
                    "hair_color", "hair_length", "hair_texture", "hair_style", "top",
                    "outerwear", "bottom", "shoes", "hat_type", "hat_color", "glasses",
                    "facial_hair", "accessories", "special_features"]
    for i, key in enumerate(display_keys):
        target = c1 if i < 10 else c2
        target.write(f"**{LABELS[key]}:** {category_text(features, key)}")
    st.write(f"**마지막 목격 위치:** {category_text(features, 'last_seen_location')}")
    st.write(f"**재난문자 발송 지역:** {category_text(features, 'alert_area')}")
    if features.get("ambiguity_notes"):
        st.info(features["ambiguity_notes"])
    with st.expander("이미지 생성 AI에 전달하는 설명 확인"):
        st.code(build_generation_prompt(features, ""), language=None)
        st.caption("이름·목격 위치·발송 지역은 이미지 생성 조건에서 제외합니다.")

if result:
    st.subheader("2. 전신 참고 이미지와 검수 결과")
    if (message, mode) != (result["message"], result["mode"]):
        st.info("아래는 이전 입력의 결과입니다. 변경한 입력을 반영하려면 다시 생성해 주세요.")
    best = result["best"]
    verdict = best["verification"]
    st.caption(f"{result['mode']} · 첫 이미지까지 {result['first_image_seconds']:.1f}초 · "
               f"검수 포함 총 {result['total_seconds']:.1f}초 · "
               f"{result['width']}×{result['height']}px · 총 {result['attempts']}회 생성")
    st.caption("각 요청에서 측정한 시간입니다. 속도·인상착의 정확도를 보장하지 않습니다.")
    st.image(best["image"], caption=f"{best['attempt']}차 생성 결과", use_container_width=True)
    if not verdict["available"]:
        st.warning("자동 검수를 완료하지 못했습니다. 생성 이미지를 보존했으며 사람이 확인해야 합니다.")
    elif verdict["pass"]:
        st.success("자동 검수를 통과한 이미지입니다.")
    else:
        st.warning("자동 검수를 통과하지 못했습니다. 표시된 이미지를 직접 확인해 주세요.")
    if result["interrupted"]:
        st.warning("추가 생성이 중단되어 앞서 생성한 결과를 표시합니다.")
    for key, label in (("missing", "누락된 항목"), ("wrong", "잘못 표현된 항목")):
        if verdict[key]:
            st.write(f"**{label}:** " + ", ".join(map(str, verdict[key])))
    if analytics_enabled() and not result["analytics_saved"]:
        st.caption("이번 결과의 전체 통계 저장에 실패했습니다. 브라우저 완료 횟수에는 반영했습니다.")
    with st.expander("이 결과의 재난문자 원문"):
        st.write(result["message"])

if result or st.session_state.get("generation_error"):
    if st.button("다시 생성하기", type="primary", use_container_width=True):
        st.session_state["regenerate_requested"] = True
        st.rerun()
