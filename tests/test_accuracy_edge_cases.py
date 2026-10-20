"""Regression cases for traits found missing during iterative alert-text sweeps."""

import pytest

from preview_logic import enhance_features_from_text
from app import sync_prompt_text_from_structured_features


def analyze(text):
    return sync_prompt_text_from_structured_features(enhance_features_from_text({}, text, ""))


@pytest.mark.parametrize(
    "text,expected,english",
    [
        ("피부가 살짝 탄 편", "살짝 그을린 피부톤", "slightly tanned skin tone"),
        ("구릿빛 피부", "구릿빛 피부톤", "subtle warm bronze skin tone"),
        ("까무잡잡한 피부", "살짝 어두운 피부톤", "slightly deeper, naturally brown skin tone"),
        ("피부는 약간 어두운 편", "살짝 어두운 피부톤", "slightly deeper, naturally brown skin tone"),
        ("피부가 살짝 탔어요", "살짝 그을린 피부톤", "slightly tanned skin tone"),
    ],
)
def test_subtle_skin_tone_is_extracted_and_added_to_image_prompt(text, expected, english):
    facts = analyze(text)
    assert facts["skin_tone"] == expected
    assert english in facts["image_prompt_en"]


@pytest.mark.parametrize(
    "text,expected,english",
    [
        ("리젠트컷", "리젠트컷", "regent haircut"),
        ("아이비리그컷", "아이비리그컷", "Ivy League haircut"),
        ("크롭컷", "크롭컷", "textured crop haircut"),
        ("쉼표머리", "쉼표머리", "comma hair"),
        ("가르마머리", "가르마머리", "side-parted hairstyle"),
        ("반곱슬 머리", "", "slightly curly hair"),
    ],
)
def test_more_hair_variants_reach_the_image_prompt(text, expected, english):
    facts = analyze(text)
    if expected:
        assert facts["hair_style"] == expected
    else:
        assert facts["hair_texture"] == "반곱슬"
    assert english in facts["image_prompt_en"]


@pytest.mark.parametrize(
    "text",
    [
        "가방이 없음",
        "가방 미착용",
        "가방을 메지 않음",
        "가방을 들고 있지 않음",
    ],
)
def test_bag_absence_is_not_mistaken_for_a_carried_bag(text):
    facts = enhance_features_from_text({}, text, "")
    assert not facts["accessories"]


def test_negated_bag_does_not_hide_an_explicitly_carried_umbrella():
    facts = enhance_features_from_text({}, "가방 없음, 우산 소지", "")
    assert facts["accessories"] == "우산"


def test_eyewear_absence_is_explicit_and_reaches_the_image_prompt():
    facts = analyze("안경을 착용하지 않음")
    assert facts["glasses"] == "없음"
    from app import build_generation_prompt

    assert "no glasses or sunglasses" in build_generation_prompt(facts, "")


@pytest.mark.parametrize("text", ["선글라스 없음", "돋보기 안경을 쓰지 않음"])
def test_all_eyewear_variants_handle_negation(text):
    assert analyze(text)["glasses"] == "없음"


def test_short_glasses_negation_is_not_misread_as_worn():
    assert analyze("안경 안 씀")["glasses"] == "없음"


def test_rare_clothing_terms_are_preserved_for_generation():
    facts = analyze("브이넥 니트, 청자켓")
    assert "브이넥" in facts["top"]
    assert "니트" in facts["top"]
    assert "denim jacket" in facts["image_prompt_en"]
    assert "V-neck" in facts["image_prompt_en"]


def test_gait_and_piercing_are_visual_features():
    facts = analyze("왼쪽 다리를 절뚝거리며 걷고 왼쪽 귀에 피어싱")
    assert "왼쪽 다리 절뚝거리는 보행" in facts["special_features"]
    assert "왼쪽 귀 피어싱" in facts["special_features"]
    assert "left leg" in facts["image_prompt_en"]
    assert "left ear" in facts["image_prompt_en"]


def test_outerwear_and_hat_absence_do_not_turn_into_positive_items():
    facts = analyze("점퍼 안 입음, 모자 미착용")
    assert facts["outerwear"] == "없음"
    assert facts["hat_type"] == "없음"
    from app import build_generation_prompt

    prompt = build_generation_prompt(facts, "")
    assert "Do not add a coat, jacket, hoodie, or other outerwear" in prompt
    assert "wears no hat or head covering" in prompt


@pytest.mark.parametrize(
    "text,expected",
    [("흑발", "검은색"), ("백금발", "백금발"), ("금발", "금발"), ("은발", "은색")],
)
def test_common_hair_color_aliases_are_extracted(text, expected):
    assert enhance_features_from_text({}, text, "")["hair_color"] == expected


def test_socks_only_is_distinct_from_bare_feet():
    facts = enhance_features_from_text({}, "양말만 신고 있음", "")
    assert facts["shoes"] == "양말만 착용"


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("오른쪽 팔에 문신", "special_features", "오른쪽 팔에 문신"),
        ("눈 밑에 큰 점", "special_features", "눈 밑에 큰 점"),
        ("왼쪽 발목에 깁스", "special_features", "왼쪽 발목 깁스"),
        ("왼쪽 발목 보호대 착용", "accessories", "발목 보호대"),
    ],
)
def test_body_marks_and_support_items_are_preserved(text, key, expected):
    facts = analyze(text)
    assert expected in facts[key]


def test_explicit_bare_feet_and_no_top_reach_image_description_and_constraints():
    facts = enhance_features_from_text({}, "상의 미착용, 신발 없음", "")
    assert facts["top"] == "상의 미착용"
    assert facts["shoes"] == "맨발"
    from app import build_generation_prompt

    prompt = build_generation_prompt(facts, "")
    assert "non-sexual, neutral, and age-appropriate" in prompt
    assert "barefoot" in prompt

