from preview_logic import category_text, enhance_features_from_text, visual_facts


def test_hairstyle_brands_and_body_type():
    facts = enhance_features_from_text(
        {},
        "상의 검은색 반팔티 (나이키), 하의 파란색 청바지 (리바이스), "
        "투블럭 머리, 비만, 마지막 목격 장소: 서울역",
        "",
    )
    assert facts["hair_style"] == "투블럭"
    assert facts["body_type"] == "비만"
    assert facts["top_brand"] == "나이키"
    assert facts["bottom_brand"] == "리바이스"
    assert category_text(facts, "top") == "검은색 반팔티 (나이키)"
    assert facts["last_seen_location"] == "서울역"
    assert "two-block haircut" in facts["image_prompt_en"]
    assert "obese build" in facts["image_prompt_en"]
    assert "last_seen_location" not in visual_facts(facts)


def test_explicit_details_override_original():
    facts = enhance_features_from_text(
        {"top": "흰색 반팔티", "hair_style": "단발"},
        "흰색 반팔티, 단발", "상의 검은색 반팔티 (나이키), 장발",
    )
    assert "검은색" in facts["top"]
    assert facts["top_brand"] == "나이키"
    assert facts["hair_style"] == "장발"


def test_brand_does_not_leak_to_unrelated_garment():
    facts = enhance_features_from_text({}, "나이키 운동화, 검은색 반팔티", "")
    assert facts["shoes_brand"] == "나이키"
    assert not facts.get("top_brand")


def test_missing_information_is_not_invented():
    facts = enhance_features_from_text({}, "검은색 반팔티, 마지막 목격 장소 서울역", "")
    assert not facts.get("body_type")
    assert not facts.get("hair_style")
    assert not facts.get("top_brand")
    assert "서울역" not in facts.get("image_prompt_en", "")
