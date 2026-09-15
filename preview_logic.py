"""Testable rules for the isolated FindVision AI preview."""

from __future__ import annotations

import re
from typing import Any

VISUAL_FIELDS = (
    "gender",
    "age",
    "height",
    "weight",
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
    "outerwear_closure",
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
)

APPEARANCE_FIELDS = (
    "skin_tone",
    "hair_color",
    "hair_length",
    "hair_texture",
    "top",
    "outerwear",
    "bottom",
    "shoes",
    "hat_type",
    "hat_color",
    "glasses",
    "facial_hair",
    "accessories",
    "special_features",
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


def analysis_message(original: str, details: str) -> str:
    """Keep the two sources distinct and give explicit supplemental facts priority."""
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


def _find_color_before(text: str, noun_pattern: str) -> str:
    match = re.search(rf"((?:검은|검정|흰|하얀|회색|빨간|붉은|파란|남색|초록|노란|베이지|갈색)색?)\s*{noun_pattern}", text)
    if not match:
        return ""
    color = match.group(1)
    aliases = {"검은": "검은색", "검정": "검은색", "흰": "흰색", "하얀": "흰색"}
    return aliases.get(color, color)


def _color_in(value: str) -> str:
    match = re.search(r"(검은색|검정색|흰색|하얀색|회색|빨간색|붉은색|파란색|남색|초록색|노란색|베이지색|갈색)", value)
    if not match:
        return ""
    color = match.group(1)
    return {"검정색": "검은색", "하얀색": "흰색"}.get(color, color)


def _extract_clothing(text: str, clothing_words: str) -> str:
    pattern = (
        rf"((?:검은|검정|흰|하얀|회색|빨간|붉은|파란|남색|초록|노란|베이지|갈색)색?\s*)?"
        rf"((?:로고\s*(?:있는|없는)|무지|긴팔|반팔|긴|짧은)\s*)*"
        rf"({clothing_words})"
    )
    matches = list(re.finditer(pattern, text))
    if not matches:
        return ""
    match = max(
        matches,
        key=lambda item: len("".join(part or "" for part in item.groups())),
    )
    color = match.group(1) or ""
    descriptors = match.group(2) or ""
    item = match.group(3)
    return _merge_words(color.strip(), descriptors.strip(), item.strip())


def _apply_text_facts(features: dict[str, Any], text: str, overwrite: bool = False) -> None:
    if not text.strip():
        return

    if overwrite or not _has_value(features, "skin_tone"):
        skin_match = re.search(r"피부(?:톤|는)?\s*(밝은\s*편|어두운\s*편|보통|희고|검은\s*편)", text)
        if skin_match:
            features["skin_tone"] = skin_match.group(1).replace(" ", " ")

    if overwrite or not _has_value(features, "hair_color"):
        hair_color = _find_color_before(text, r"(?:머리|머리색)")
        if not hair_color:
            color_match = re.search(r"머리색\s*((?:검은|검정|흰|하얀|회색|갈색|노란)색?)", text)
            hair_color = color_match.group(1) if color_match else ""
        if hair_color:
            features["hair_color"] = {"검은": "검은색", "검정": "검은색"}.get(hair_color, hair_color)

    if overwrite or not _has_value(features, "hair_length"):
        length_match = re.search(r"머리(?:길이)?\s*(약간\s*짧음|짧음|짧은|긴|중간)", text)
        if length_match:
            features["hair_length"] = length_match.group(1).replace("짧은", "짧음")

    if "직모" in text and (overwrite or not _has_value(features, "hair_texture")):
        features["hair_texture"] = "직모"
    if "곱슬" in text and (overwrite or not _has_value(features, "hair_texture")):
        features["hair_texture"] = "곱슬"

    for style in ("버섯머리", "반삭머리", "단발", "스포츠머리"):
        if style in text and (overwrite or not _has_value(features, "hair_style")):
            features["hair_style"] = style
            break

    top = _extract_clothing(text, r"(?:반팔티|반팔\s*상의|긴팔티|티셔츠|상의|셔츠|니트)")
    existing_top = str(features.get("top", "") or "")
    if top and (overwrite or not _has_value(features, "top")):
        if "반팔" in existing_top and "반팔" not in top:
            top = _merge_words(top, "반팔")
        if "긴팔" in existing_top and "긴팔" not in top:
            top = _merge_words(top, "긴팔")
        features["top"] = top
    elif top and "반팔" in top and "반팔" not in str(features.get("top", "")):
        features["top"] = _merge_words(str(features.get("top", "")), "반팔")
    if re.search(r"(?:브랜드\s*)?없음|브랜드\s*없", text) and _has_value(features, "top"):
        features["top_brand"] = ""

    bottom = _extract_clothing(text, r"(?:반바지|긴바지|바지)")
    if bottom and (overwrite or not _has_value(features, "bottom")):
        existing_color = _color_in(str(features.get("bottom", "") or ""))
        if existing_color and not _color_in(bottom):
            bottom = _merge_words(existing_color, bottom)
        features["bottom"] = bottom

    shoes = _extract_clothing(text, r"(?:크록스|운동화|구두|슬리퍼|신발)")
    if shoes and (overwrite or not _has_value(features, "shoes")):
        existing_color = _color_in(str(features.get("shoes", "") or ""))
        if existing_color and not _color_in(shoes):
            shoes = _merge_words(existing_color, shoes)
        features["shoes"] = shoes
    if "크록스" in str(features.get("shoes", "")) or re.search(r"크록스", text):
        features["shoes_brand"] = "크록스"

    hat_color = _find_color_before(text, r"(?:모자|캡모자|야구모자)")
    if "캡모자" in text or "야구모자" in text:
        if overwrite or not _has_value(features, "hat_type"):
            features["hat_type"] = "캡모자"
    elif "모자" in text and (overwrite or not _has_value(features, "hat_type")):
        features["hat_type"] = "모자(종류 불명)"
    if hat_color and (overwrite or not _has_value(features, "hat_color")):
        features["hat_color"] = hat_color

    if re.search(r"안경\s*(?:쓰|착용|있)", text) and (overwrite or not _has_value(features, "glasses")):
        features["glasses"] = "안경"
    if re.search(r"수염\s*없", text) and (overwrite or not _has_value(features, "facial_hair")):
        features["facial_hair"] = "없음"
    if re.search(r"작은\s*가방|가방", text) and (overwrite or not _has_value(features, "accessories")):
        features["accessories"] = "작은가방"


def enhance_features_from_text(features: dict[str, Any], original: str, details: str) -> dict[str, Any]:
    """Recover explicitly written Korean facts when the model leaves fields blank."""
    enhanced = dict(features)
    _apply_text_facts(enhanced, original, overwrite=False)
    _apply_text_facts(enhanced, details, overwrite=True)
    return enhanced


def visual_facts(features: dict[str, Any]) -> dict[str, str]:
    """Exclude name and locations from the image/vision requirements."""
    return {
        key: str(features.get(key, "") or "").strip()
        for key in VISUAL_FIELDS
        if str(features.get(key, "") or "").strip()
    }


def category_text(features: dict[str, Any], key: str) -> str:
    value = str(features.get(key, "") or "").strip() or "정보 없음"
    metadata = METADATA.get(key)
    if metadata:
        meta_key, meta_label = metadata
        meta_value = str(features.get(meta_key, "") or "").strip() or "정보 없음"
        return f"{value} ({meta_label}: {meta_value})"
    return value


def known_appearance_count(features: dict[str, Any]) -> int:
    return sum(bool(str(features.get(key, "") or "").strip()) for key in APPEARANCE_FIELDS)


def missing_recommended(features: dict[str, Any]) -> list[str]:
    expected = (("top", "상의"), ("outerwear", "겉옷"), ("bottom", "하의"), ("shoes", "신발"))
    missing = [label for key, label in expected if not str(features.get(key, "") or "").strip()]
    if features.get("outerwear") and not features.get("top"):
        missing = [label for label in missing if label != "상의"]
    if features.get("top") and not features.get("outerwear"):
        missing = [label for label in missing if label != "겉옷"]
    return missing


def safe_count(value: Any) -> int:
    """A browser cookie is untrusted input, so cap its display value."""
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
        "pass": normalize_bool(parsed.get("pass"))
        and score >= minimum_score
        and not missing
        and not wrong,
        "missing": missing,
        "wrong": wrong,
        "has_text": has_text,
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
