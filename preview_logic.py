"""Testable Korean appearance extraction rules for FindVision AI.

Recover only explicit facts: never infer body size from weight or put a last-seen
location into the image prompt.
"""

from __future__ import annotations

import re
from typing import Any

VISUAL_FIELDS = (
    "gender", "age", "height", "weight", "body_type", "nationality",
    "skin_tone", "hair_color", "hair_length", "hair_texture", "hair_style",
    "top", "top_brand", "outerwear", "outerwear_brand", "bottom",
    "bottom_brand", "shoes", "shoes_brand", "hat_type", "hat_color",
    "hat_brand", "glasses", "facial_hair", "accessories", "special_features",
)
APPEARANCE_FIELDS = (
    "skin_tone", "hair_color", "hair_length", "hair_texture", "body_type",
    "hair_style", "top", "outerwear", "bottom", "shoes", "hat_type",
    "hat_color", "glasses", "facial_hair", "accessories", "special_features",
)
METADATA = {
    "hair_color": ("hair_style", "스타일"),
    "hair_length": ("hair_style", "스타일"),
    "hair_texture": ("hair_style", "스타일"),
    "top": ("top_brand", "브랜드"),
    "outerwear": ("outerwear_brand", "브랜드"),
    "bottom": ("bottom_brand", "브랜드"),
    "shoes": ("shoes_brand", "브랜드"),
    "hat_type": ("hat_brand", "브랜드"),
    "hat_color": ("hat_brand", "브랜드"),
}
COLORS = r"검은색|검정색|검은|검정|흰색|하얀색|흰|하얀|회색|빨간색|빨간|붉은색|붉은|파란색|파란|남색|초록색|초록|노란색|노란|베이지색|베이지|갈색|분홍색|분홍|보라색|보라|주황색|주황"
BRANDS = (
    "뉴발란스", "아디다스", "나이키", "푸마", "언더아머", "데상트", "휠라",
    "노스페이스", "디스커버리", "내셔널지오그래픽", "유니클로", "무신사",
    "스파오", "아식스", "컨버스", "반스", "크록스", "리바이스", "폴로",
    "블랙야크", "K2", "MLB", "Nike", "Adidas", "Puma", "New Balance",
    "The North Face", "Uniqlo", "Crocs",
)
HAIRSTYLES = (
    "투블럭컷", "투블럭", "버섯머리", "장발", "긴머리", "울프컷", "히피펌",
    "가르마펌", "리프컷", "댄디컷", "포마드", "스포츠머리", "반삭머리",
    "반삭", "삭발", "숏컷", "단발머리", "단발", "보브컷", "포니테일",
    "묶은머리", "땋은머리", "곱슬머리", "파마머리", "파마",
)
CLOTHES = {
    "top": r"반팔\s*티(?:셔츠)?|긴팔\s*티(?:셔츠)?|티셔츠|맨투맨|후드티|폴로티|카라티|셔츠|니트|상의",
    "outerwear": r"후드\s*집업|바람막이|패딩|점퍼|자켓|재킷|코트|외투|겉옷|조끼|작업복",
    "bottom": r"반바지|긴바지|청바지|슬랙스|치마|레깅스|바지|하의",
    "shoes": r"운동화|크록스|슬리퍼|샌들|구두|단화|부츠|신발",
    "hat_type": r"캡모자|야구모자|벙거지|버킷햇|비니|중절모|모자",
}


def analysis_message(original: str, details: str) -> str:
    original = original.strip()
    details = details.strip()
    if not original:
        raise ValueError("실종 재난문자 원문을 입력해 주세요.")
    return (
        "[실종 재난문자 원문 — 수정하지 않은 텍스트]\n"
        f"{original}\n\n"
        "[사용자가 추가한 상세 설명 — 원문과 충돌하면 이 설명을 우선]\n"
        f"{details if details else '추가 설명 없음'}"
    )


def _has_value(features: dict[str, Any], key: str) -> bool:
    return bool(str(features.get(key, "") or "").strip())


def _merge_words(*parts: str) -> str:
    words: list[str] = []
    for part in parts:
        for word in re.split(r"\s+", str(part or "").strip()):
            if word and word not in words:
                words.append(word)
    return " ".join(words)


def _normalize_color(value: str) -> str:
    return {
        "검은": "검은색", "검정": "검은색", "검정색": "검은색",
        "흰": "흰색", "하얀": "흰색", "하얀색": "흰색",
        "빨간": "빨간색", "붉은": "붉은색", "파란": "파란색",
        "초록": "초록색", "노란": "노란색", "베이지": "베이지색",
        "분홍": "분홍색", "보라": "보라색", "주황": "주황색",
    }.get(value, value)


def _find_color_before(text: str, noun_pattern: str) -> str:
    match = re.search(rf"({COLORS})\s*{noun_pattern}", text)
    return _normalize_color(match.group(1)) if match else ""


def _color_in(value: str) -> str:
    match = re.search(rf"({COLORS})", value)
    return _normalize_color(match.group(1)) if match else ""


def _extract_clothing(text: str, clothing_words: str) -> str:
    pattern = (
        rf"({COLORS})?\s*"
        rf"((?:(?:로고\s*(?:있는|없는)|무지|긴팔|반팔|긴|짧은)\s*)*)"
        rf"({clothing_words})"
    )
    matches = list(re.finditer(pattern, text))
    if not matches:
        return ""
    match = max(matches, key=lambda item: len("".join(part or "" for part in item.groups())))
    return _merge_words(_normalize_color(match.group(1) or ""), match.group(2), match.group(3))


def _explicit_brand(text: str, key: str) -> str | None:
    """Associate brands with garments, not merely with the whole message."""
    item = CLOTHES[key]
    label = {
        "top": r"상의|티셔츠|반팔티|긴팔티",
        "outerwear": r"겉옷|외투|아우터",
        "bottom": r"하의|바지",
        "shoes": r"신발",
        "hat_type": r"모자",
    }[key]
    brands = "|".join(re.escape(brand) for brand in BRANDS)
    if re.search(rf"(?:{label})\s*브랜드\s*(?:없음|없다|없)", text):
        return ""
    patterns = (
        rf"(?:{label})\s*브랜드\s*[:：]?\s*({brands})(?![가-힣A-Za-z])",
        rf"(?:{item})\s*\(\s*({brands})\s*\)",
        rf"({brands})\s*(?:{COLORS})?\s*(?:반팔|긴팔|로고있는|로고 없는)?\s*(?:{item})",
        rf"(?:{label})\s*[:：]?\s*(?:{COLORS})?\s*(?:반팔|긴팔)?\s*(?:{item})\s*\(?\s*({brands})\s*\)?",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            brand = match.group(1)
            return next((known for known in BRANDS if known.casefold() == brand.casefold()), brand)
    return None


def _apply_text_facts(features: dict[str, Any], text: str, overwrite: bool = False) -> None:
    if not text.strip():
        return
    if overwrite or not _has_value(features, "skin_tone"):
        match = re.search(r"피부(?:톤|는)?\s*(밝은\s*편|어두운\s*편|보통|희고|검은\s*편)", text)
        if match:
            features["skin_tone"] = match.group(1)
    if overwrite or not _has_value(features, "hair_color"):
        color = _find_color_before(text, r"(?:머리|머리색)")
        if not color:
            match = re.search(rf"머리색\s*({COLORS})", text)
            color = _normalize_color(match.group(1)) if match else ""
        if color:
            features["hair_color"] = color
    if overwrite or not _has_value(features, "hair_length"):
        match = re.search(r"머리(?:길이)?\s*(약간\s*짧음|짧음|짧은|긴|중간|장발)", text)
        if match:
            features["hair_length"] = match.group(1).replace("짧은", "짧음")
    if "직모" in text and (overwrite or not _has_value(features, "hair_texture")):
        features["hair_texture"] = "직모"
    if "곱슬" in text and (overwrite or not _has_value(features, "hair_texture")):
        features["hair_texture"] = "곱슬"
    for style in HAIRSTYLES:
        if style in text and (overwrite or not _has_value(features, "hair_style")):
            features["hair_style"] = {
                "투블럭컷": "투블럭", "긴머리": "장발",
                "반삭머리": "반삭", "단발머리": "단발",
            }.get(style, style)
            break
    if overwrite or not _has_value(features, "body_type"):
        match = re.search(r"(고도\s*비만|비만|저체중|통통한\s*편|마른\s*편|마름|뚱뚱한\s*편|건장한\s*편|보통\s*체형)", text)
        if match:
            features["body_type"] = {"마름": "마른 편"}.get(match.group(1), match.group(1))
    for key in ("top", "outerwear", "bottom", "shoes"):
        found = _extract_clothing(text, CLOTHES[key])
        if not found:
            continue
        existing = str(features.get(key, "") or "")
        if overwrite or not _has_value(features, key):
            if key == "top":
                for sleeve in ("반팔", "긴팔"):
                    if sleeve in existing and sleeve not in found:
                        found = _merge_words(found, sleeve)
            if key in {"bottom", "shoes"} and not _color_in(found):
                found = _merge_words(_color_in(existing), found)
            features[key] = found
        elif key == "top" and "반팔" in found and "반팔" not in existing:
            features[key] = _merge_words(existing, "반팔")
    for key, brand_key in (
        ("top", "top_brand"), ("outerwear", "outerwear_brand"),
        ("bottom", "bottom_brand"), ("shoes", "shoes_brand"),
        ("hat_type", "hat_brand"),
    ):
        brand = _explicit_brand(text, key)
        if brand is not None and (overwrite or not _has_value(features, brand_key)):
            features[brand_key] = brand
    if re.search(r"상의와\s*하의\s*브랜드\s*없", text):
        features["top_brand"] = ""
        features["bottom_brand"] = ""
    if "크록스" in str(features.get("shoes", "")) and not _has_value(features, "shoes_brand"):
        features["shoes_brand"] = "크록스"
    match = re.search(r"(아디다스|나이키|푸마|뉴발란스)\s*(?:슬리퍼|신발|운동화|크록스|구두)", text)
    if match and (overwrite or not _has_value(features, "shoes_brand")):
        features["shoes_brand"] = match.group(1)
        if _has_value(features, "shoes") and match.group(1) not in str(features["shoes"]):
            features["shoes"] = _merge_words(match.group(1), str(features["shoes"]))
    hat_color = _find_color_before(text, r"(?:캡모자|야구모자|벙거지|버킷햇|비니|모자)")
    hat_kind = next((kind for kind in ("캡모자", "야구모자", "벙거지", "버킷햇", "비니", "중절모") if kind in text), "")
    if hat_kind and (overwrite or not _has_value(features, "hat_type")):
        features["hat_type"] = "캡모자" if hat_kind == "야구모자" else hat_kind
    elif "모자" in text and (overwrite or not _has_value(features, "hat_type")):
        features["hat_type"] = "모자(종류 불명)"
    if hat_color and (overwrite or not _has_value(features, "hat_color")):
        features["hat_color"] = hat_color
    if re.search(r"안경\s*(?:쓰|착용|있)", text) and (overwrite or not _has_value(features, "glasses")):
        features["glasses"] = "안경"
    if re.search(r"수염\s*없", text) and (overwrite or not _has_value(features, "facial_hair")):
        features["facial_hair"] = "없음"
    accessory_terms: list[str] = []
    for pattern, label in (
        (r"작은\s*가방", "작은가방"), (r"백팩", "백팩"),
        (r"가방", "가방"), (r"휴대폰|핸드폰|스마트폰", "휴대폰"),
        (r"지갑", "지갑"), (r"우산", "우산"),
        (r"목걸이", "목걸이"), (r"팔찌", "팔찌"),
        (r"시계", "시계"), (r"소지품\s*([가-힣A-Za-z0-9]+)", ""),
    ):
        match = re.search(pattern, text)
        if match:
            value = match.group(1) if not label and match.groups() else label
            if value and value not in accessory_terms:
                accessory_terms.append(value)
    if accessory_terms and (overwrite or not _has_value(features, "accessories")):
        features["accessories"] = _merge_words(str(features.get("accessories", "") or ""), *accessory_terms)
    location = re.search(r"(?:마지막\s*(?:목격|확인)\s*(?:위치|장소)|목격\s*(?:위치|장소))\s*[:：은는]?\s*([^,.\n]+)", text)
    if location and (overwrite or not _has_value(features, "last_seen_location")):
        features["last_seen_location"] = location.group(1).strip()
    alert_area = re.search(r"(?:재난문자\s*)?발송\s*지역\s*[:：은는]?\s*([^,.\n]+)", text)
    if alert_area and (overwrite or not _has_value(features, "alert_area")):
        features["alert_area"] = alert_area.group(1).strip()


def enhance_features_from_text(features: dict[str, Any], original: str, details: str) -> dict[str, Any]:
    """Recover explicit facts; vetted additions override raw text."""
    enhanced = dict(features)
    _apply_text_facts(enhanced, original, overwrite=False)
    _apply_text_facts(enhanced, details, overwrite=True)
    styles = {
        "투블럭": "two-block haircut, closely trimmed sides and back with longer hair on top",
        "버섯머리": "mushroom bowl haircut with an even rounded fringe",
        "장발": "long hair", "단발": "bob haircut",
        "반삭": "very short buzz cut", "삭발": "shaved head",
        "숏컷": "short haircut", "스포츠머리": "short athletic haircut",
        "울프컷": "wolf cut haircut", "포니테일": "hair tied in a ponytail",
        "가르마펌": "side-parted permed haircut",
    }
    builds = {
        "마른 편": "slim build", "저체중": "underweight build",
        "통통한 편": "stocky build", "뚱뚱한 편": "heavy build",
        "비만": "obese build", "고도 비만": "very heavy build",
        "건장한 편": "sturdy build", "보통 체형": "average build",
    }
    hints: list[str] = []
    style = str(enhanced.get("hair_style", "") or "").strip()
    if style in styles:
        hints.append("Haircut: " + styles[style])
    body = str(enhanced.get("body_type", "") or "").strip()
    if body in builds:
        hints.append("Body: " + builds[body])
    for garment, brand in (
        ("top", "top_brand"), ("outerwear", "outerwear_brand"),
        ("bottom", "bottom_brand"), ("shoes", "shoes_brand"),
        ("hat_type", "hat_brand"),
    ):
        if _has_value(enhanced, garment) and _has_value(enhanced, brand):
            hints.append(f"{garment} brand reference: {enhanced[brand]} (style only; no text or logo)")
    if hints:
        suffix = "Explicit detail hints: " + "; ".join(hints)
        existing = str(enhanced.get("image_prompt_en", "") or "").strip()
        if suffix not in existing:
            enhanced["image_prompt_en"] = existing + ("\n" if existing else "") + suffix
    return enhanced


def visual_facts(features: dict[str, Any]) -> dict[str, str]:
    """Exclude name and both location fields from visual requirements."""
    return {key: str(features.get(key, "") or "").strip() for key in VISUAL_FIELDS if _has_value(features, key)}


def category_text(features: dict[str, Any], key: str) -> str:
    value = str(features.get(key, "") or "").strip() or "정보 없음"
    metadata = METADATA.get(key)
    if metadata:
        meta_key, meta_label = metadata
        meta_value = str(features.get(meta_key, "") or "").strip() or "정보 없음"
        if meta_label == "브랜드" and meta_value != "정보 없음":
            return f"{value} ({meta_value})"
        return f"{value} ({meta_label}: {meta_value})"
    return value


def known_appearance_count(features: dict[str, Any]) -> int:
    return sum(_has_value(features, key) for key in APPEARANCE_FIELDS)


def missing_recommended(features: dict[str, Any]) -> list[str]:
    expected = (("top", "상의"), ("outerwear", "겉옷"), ("bottom", "하의"), ("shoes", "신발"))
    missing = [label for key, label in expected if not _has_value(features, key)]
    if _has_value(features, "outerwear") and not _has_value(features, "top"):
        missing = [label for label in missing if label != "상의"]
    if _has_value(features, "top") and not _has_value(features, "outerwear"):
        missing = [label for label in missing if label != "겉옷"]
    return missing


def safe_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 0
    return min(max(count, 0), 1_000_000)


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def verification_result(parsed: dict[str, Any], raw: str = "", minimum_score: int = 80) -> dict:
    try:
        score = max(0, min(int(parsed.get("score", 0)), 100))
    except (TypeError, ValueError):
        score = 0
    missing = parsed.get("missing") or []
    wrong = parsed.get("wrong") or []
    missing = missing if isinstance(missing, list) else [str(missing)]
    wrong = wrong if isinstance(wrong, list) else [str(wrong)]
    missing = [str(item) for item in missing if str(item).strip()]
    wrong = [str(item) for item in wrong if str(item).strip()]
    has_text = normalize_bool(parsed.get("has_text"))
    if has_text:
        wrong.append("이미지 안에 글자가 있음")
    return {
        "score": score,
        "pass": normalize_bool(parsed.get("pass")) and score >= minimum_score and not missing and not wrong,
        "missing": missing, "wrong": wrong, "has_text": has_text,
        "feedback_en": str(parsed.get("feedback_en", "") or "").strip(),
        "raw": raw,
    }


def image_mime(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"
