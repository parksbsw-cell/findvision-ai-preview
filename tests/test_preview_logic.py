from preview_logic import (
    analysis_message,
    category_text,
    image_mime,
    known_appearance_count,
    missing_recommended,
    safe_count,
    verification_result,
    visual_facts,
)


def test_raw_alert_and_details_remain_separate():
    text = analysis_message(" [원문] 빨간 상의 ", " 겉옷은 파란 점퍼 ")
    assert "[원문] 빨간 상의" in text
    assert "겉옷은 파란 점퍼" in text
    assert text.index("[원문]") < text.index("겉옷은")


def test_brand_and_hair_style_use_information_none():
    assert category_text({"outerwear": "파란 점퍼"}, "outerwear") == (
        "파란 점퍼 (브랜드: 정보 없음)"
    )
    assert category_text({"hair_texture": "곱슬", "hair_style": "단발"}, "hair_texture") == (
        "곱슬 (스타일: 단발)"
    )


def test_outerwear_is_a_valid_appearance_field():
    facts = {"outerwear": "흰색 외투", "bottom": "검은 바지", "shoes": "단화"}
    assert known_appearance_count(facts) == 3
    assert missing_recommended(facts) == []


def test_location_and_name_never_become_visual_facts():
    facts = visual_facts(
        {
            "name": "가상 이름",
            "last_seen_location": "서울역",
            "alert_area": "서울",
            "outerwear": "흰색 외투",
        }
    )
    assert facts == {"outerwear": "흰색 외투"}


def test_browser_count_is_bounded():
    assert safe_count("4") == 4
    assert safe_count("oops") == 0
    assert safe_count("-5") == 0


def test_vision_verdict_requires_score_and_real_boolean():
    base = {"score": 95, "pass": "false", "missing": [], "wrong": [], "has_text": "false"}
    assert verification_result(base)["pass"] is False
    assert verification_result({**base, "pass": True, "score": 79})["pass"] is False
    assert verification_result({**base, "pass": True, "score": 80})["pass"] is True


def test_generated_image_format_is_detected():
    assert image_mime(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert image_mime(b"\xff\xd8\xffrest") == "image/jpeg"
