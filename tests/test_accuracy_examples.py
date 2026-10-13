"""Twenty fictional regression examples for explicit Korean appearance facts."""

import pytest

from preview_logic import enhance_features_from_text

EXAMPLES = [
    ("검은색 반팔티 착용", "top", "반팔티"),
    ("흰색 긴팔 티셔츠 착용", "top", "긴팔"),
    ("파란색 반바지 착용", "bottom", "반바지"),
    ("검은색 긴바지 착용", "bottom", "바지"),
    ("흰색 크록스 착용", "shoes", "크록스"),
    ("검은색 운동화 착용", "shoes", "운동화"),
    ("회색 후드 집업 착용", "outerwear", "후드"),
    ("남색 패딩 착용", "outerwear", "패딩"),
    ("머리 스타일은 투블럭", "hair_style", "투블럭"),
    ("버섯머리", "hair_style", "버섯머리"),
    ("체형은 마른 편", "body_type", "마른 편"),
    ("체형은 통통한 편", "body_type", "통통한 편"),
    ("체형은 저체중", "body_type", "저체중"),
    ("체형은 비만", "body_type", "비만"),
    ("검은색 나이키 반팔티", "top_brand", "나이키"),
    ("흰색 크록스", "shoes_brand", "크록스"),
    ("검은색 가방 소지", "accessories", "가방"),
    ("빨간색 우산 소지", "accessories", "우산"),
    ("손목시계 착용", "accessories", "시계"),
    ("목걸이와 팔찌 착용", "accessories", "목걸이"),
]


@pytest.mark.parametrize("text,key,expected", EXAMPLES)
def test_twenty_fictional_accuracy_examples(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")


def test_examples_are_exactly_twenty():
    assert len(EXAMPLES) == 20


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("남, 76세, 168cm, 마른 체형", "body_type", "마른 편"),
        ("여성 9세 노란색 원피스 흰 운동화", "top", "원피스"),
        ("여, 82세, 꽃무늬 긴팔 상의, 검은 몸빼바지", "top", "꽃무늬"),
        ("여, 82세, 꽃무늬 긴팔 상의, 검은 몸빼바지", "bottom", "몸빼"),
    ],
)
def test_compact_disaster_message_variants(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")


def test_layered_tops_without_inner_word_are_kept_separate():
    text = "검은색 얇은 반팔티 위에 흰색 학교 반팔 셔츠를 입고 모든 단추를 풀어 입음"
    facts = enhance_features_from_text({}, text, "")
    assert "검은색" in facts["top"]
    assert "반팔" in facts["top"]
    assert "흰색" in facts["outerwear"]
    assert "학교" in facts["outerwear"]


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("곤색 잠바, 회색계열 면바지, 검정 안전화", "outerwear", "남색 잠바"),
        ("곤색 잠바, 회색계열 면바지, 검정 안전화", "bottom", "회색 면바지"),
        ("곤색 잠바, 회색계열 면바지, 검정 안전화", "shoes", "안전화"),
        ("카키색 남방, 아이보리 고무줄 바지", "top", "카키색 남방"),
        ("카키색 남방, 아이보리 고무줄 바지", "bottom", "아이보리색 고무줄 바지"),
        ("오른손에 목발, 왼손에 파란 장바구니", "accessories", "오른손에 목발"),
        ("오른손에 목발, 왼손에 파란 장바구니", "accessories", "왼손에 파란 장바구니"),
    ],
)
def test_common_disaster_message_vocabulary(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")


def test_model_cannot_swap_top_and_outerwear_categories():
    model_guess = {
        "top": "곤색 잠바",
        "outerwear": "카키색 남방",
        "bottom": "검정 안전화",
        "shoes": "회색 면바지",
    }
    text = "남, 79세, 곤색 잠바, 카키색 남방, 회색계열 면바지, 검정 안전화"
    facts = enhance_features_from_text(model_guess, text, "")
    assert facts["top"] == "카키색 남방"
    assert facts["outerwear"] == "남색 잠바"
    assert facts["bottom"] == "회색 면바지"
    assert facts["shoes"] == "검은색 안전화"
