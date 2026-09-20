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
