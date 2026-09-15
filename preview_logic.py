"""Testable rules for the isolated FindVision AI preview."""

from __future__ import annotations

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
