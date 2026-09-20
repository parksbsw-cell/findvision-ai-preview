from preview_logic import (
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


def test_analysis_message_contains_only_the_original_alert():
    text = analysis_message(" [원문] 빨간 상의 ")
    assert "[원문] 빨간 상의" in text
    assert "추가 상세 설명" not in text


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


def test_explicit_korean_details_recover_missing_clothing_and_hair():
    original = (
        "아시아인, 동양인, 남자, 17세, 키 177, 몸무게 62, 피부톤은 밝은 편, "
        "머리색 검은색, 머리길이 약간 짧음, 직모, 검은색 반팔 상의, 흰색 겉옷, "
        "검은색 반바지, 흰색 크록스, 파랑과 흰색의 섞인 모자, 버섯머리, "
        "아산스마트팩토리마이스터고등학교, 안경 쓰고있음, 수염 없음, 작은가방, 이름 김상덕"
    )
    details = (
        "상의와 하의 브랜드 없음, 아산스마트팩토리마이스터고등학교, 흰색 모자, "
        "검은색 로고있는 상의. 반바지, 머리 스타일은 버섯머리, 소지품 곰"
    )

    recovered = enhance_features_from_text({"top": "", "bottom": "", "shoes": ""}, original, details)

    assert "검은색" in recovered["top"]
    assert "반팔" in recovered["top"]
    assert "로고" in recovered["top"]
    assert recovered["bottom"] == "검은색 반바지"
    assert recovered["shoes"] == "흰색 크록스"
    assert recovered["shoes_brand"] == "크록스"
    assert recovered["hair_color"] == "검은색"
    assert recovered["hair_length"] == "약간 짧음"
    assert recovered["hair_texture"] == "직모"
    assert recovered["hair_style"] == "버섯머리"
    assert recovered["hat_color"] == "흰색"
    assert recovered["hat_type"] == "모자(종류 불명)"
    assert recovered["glasses"] == "안경"
    assert recovered["facial_hair"] == "없음"


def test_body_type_accessories_and_shoe_brand_are_recovered():
    original = (
        "국적 대한민국, 남성, 키 177, 몸무게 120, 피부톤 어두운편, "
        "상의 검은색 반팔티, 외투 회색 작업복, 하의 검은색 반바지, "
        "신발 검은색 슬리퍼, 모자 검은색 모자, 목격 위치 아산스마트팩토리마이스터고등학교"
    )
    details = "상의와 하의 브랜드 없음, 아디다스 슬리퍼, 비만, 소지품 금, 작은 가방, 시계"

    recovered = enhance_features_from_text({}, original, details)

    assert recovered["body_type"] == "비만"
    assert recovered["shoes_brand"] == "아디다스"
    assert "아디다스" in recovered["shoes"]
    assert "슬리퍼" in recovered["shoes"]
    assert "금" in recovered["accessories"]
    assert "작은가방" in recovered["accessories"]
    assert "시계" in recovered["accessories"]
    assert recovered["last_seen_location"] == "아산스마트팩토리마이스터고등학교"
