# Provider adapter snapshot from the existing Streamlit app. No Streamlit imports.

import base64
import json
import os
import re
from typing import Any

import requests

from .appearance import (
    BRANDS,
    analysis_message,
    enhance_features_from_text,
    image_mime,
    verification_result,
    visual_facts,
)


def get_secret(name: str) -> str:
    return os.environ.get(name, "").strip()

TEXT_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"

IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"

VISION_MODEL = "@cf/moondream/moondream3.1-9B-A2B"

EDITABLE_FIELDS = [
    "gender", "age", "height", "weight", "body_type", "nationality", "skin_tone",
    "hair_color", "hair_length", "hair_texture", "hair_style", "top", "top_brand",
    "outerwear", "outerwear_brand", "bottom", "bottom_brand", "shoes", "shoes_brand",
    "hat_type", "hat_color", "hat_brand", "glasses", "facial_hair", "accessories",
    "special_features", "last_seen_location", "alert_area",
]

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

def build_generation_prompt(
    features: dict,
    origin_en: str,
    correction: str = "",
) -> str:

    features = sync_prompt_text_from_structured_features(dict(features))
    description = features["image_prompt_en"]
    if not description:
        description = (
            "a Korean person with an unspecified age and build, wearing a plain, "
            "neutral contemporary outfit; no bag or accessories are specified"
        )
    nationality = str(features.get("nationality", "") or "").strip()
    nationality_en = {
        "대한민국": "Korean", "한국": "Korean", "한국인": "Korean",
        "미국": "American", "미국인": "American", "일본": "Japanese", "일본인": "Japanese",
        "중국": "Chinese", "중국인": "Chinese",
    }.get(nationality, nationality or "Korean")
    origin_instruction = (
        f"Depict the fictional person as {nationality_en}. "
        if nationality else
        "No nationality was stated; use the service default and depict the fictional person as Korean. "
    )
    layers = ("Wear the stated outerwear over the inner top. A closed outer layer may hide the top."
              if features.get("outerwear") else "No outerwear is specified; do not add a coat or jacket.")
    prompt = (
        "Create one photorealistic full-body appearance reference of a fictional person. "
        "This is an illustration of described clothing and build, not an identified person's face. "
        "Standing front view, head and feet visible, plain light background, contemporary clothing. "
        + origin_instruction +
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
