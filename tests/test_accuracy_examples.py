"""Twenty fictional regression examples for explicit Korean appearance facts."""

import pytest

from preview_logic import enhance_features_from_text, extract_age

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


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("흰색 생활복, 남색 가디건, 검은 등산 바지, 회색 실내화", "top", "생활복"),
        ("흰색 생활복, 남색 가디건, 검은 등산 바지, 회색 실내화", "outerwear", "가디건"),
        ("흰색 생활복, 남색 가디건, 검은 등산 바지, 회색 실내화", "bottom", "등산 바지"),
        ("흰색 생활복, 남색 가디건, 검은 등산 바지, 회색 실내화", "shoes", "실내화"),
        ("체크 남방, 경량 패딩, 칠부 바지, 털신", "top", "체크 남방"),
        ("체크 남방, 경량 패딩, 칠부 바지, 털신", "outerwear", "경량 패딩"),
        ("체크 남방, 경량 패딩, 칠부 바지, 털신", "bottom", "칠부 바지"),
        ("체크 남방, 경량 패딩, 칠부 바지, 털신", "shoes", "털신"),
    ],
)
def test_more_real_world_clothing_terms(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("[서울특별시] 실종자(여, 84세), 백발 단발, 보행기 사용", "gender", "여성"),
        ("[서울특별시] 실종자(여, 84세), 백발 단발, 보행기 사용", "hair_color", "백발"),
        ("남 6세, 파란 줄무늬 긴팔티, 노란 장화, 빨간 책가방", "accessories", "빨간 책가방"),
        ("남성 35세, 안에 흰 민소매, 회색 후드집업", "top", "민소매"),
        ("여 72세, 흰색 파마머리, 보라 원피스", "hair_color", "흰색"),
        ("남 50대, 빨간 체크 남방, 검정 조끼", "age", "50대"),
        ("여 20대, 검은 롱패딩, 회색 후드티", "age", "20대"),
    ],
)
def test_new_disaster_alert_edge_cases(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("남, 77세, 대머리, 회색 양복, 흰 와이셔츠, 검정 구두, 갈색 서류가방", "hair_style", "대머리"),
        ("남, 77세, 대머리, 회색 양복, 흰 와이셔츠, 검정 구두, 갈색 서류가방", "accessories", "갈색 서류가방"),
        ("여, 81세, 짧은 백발, 청록색 반팔, 검정 치마바지, 자주색 효도화", "hair_length", "짧음"),
        ("여, 81세, 짧은 백발, 청록색 반팔, 검정 치마바지, 자주색 효도화", "shoes", "효도화"),
        ("남아 7세, 노랑 민소매티, 파랑 반바지, 흰 스니커즈", "gender", "남성"),
        ("여아 5세, 양갈래머리, 분홍 원피스, 빨간 메리제인 구두, 인형 소지", "hair_style", "양갈래"),
        ("여아 5세, 양갈래머리, 분홍 원피스, 빨간 메리제인 구두, 인형 소지", "accessories", "인형"),
        ("남 40대, 청록 바람막이, 검정 카고바지, 회색 스니커즈", "bottom", "카고바지"),
        ("여 60대, 밤색 개량한복 상의, 검정 통바지, 꽃무늬 밀짚모자, 검은 쇼핑백", "hat_type", "밀짚모자"),
        ("남성, 곱슬 백발, 검정 뿔테안경, 남색 집업조끼", "glasses", "뿔테안경"),
        ("여, 73세, 회색 커트머리, 빨간 목폴라, 버건디 단화, 검은 비닐봉지", "top", "목폴라"),
        ("여, 73세, 회색 커트머리, 빨간 목폴라, 버건디 단화, 검은 비닐봉지", "accessories", "비닐봉지"),
    ],
)
def test_additional_unseen_alert_vocabulary(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")


def test_negated_crossbody_bag_is_not_added():
    facts = enhance_features_from_text({}, "남 40대, 검정 카고바지, 크로스백 미소지", "")
    assert not facts.get("accessories")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("실종자 남성, 만 78세, 회색 점퍼", "78세"),
        ("여아 8살, 분홍 원피스", "8세"),
        ("나이: 81 세, 검정 바지", "81세"),
        ("70대 후반 남성, 남색 모자", "70대 후반"),
        ("40대 중반 여성, 흰 운동화", "40대 중반"),
        ("70~80세 추정, 회색 상의", "70~80세"),
        ("50-60대 추정 남성", "50~60대"),
        ("2015년생 남아, 파란 반팔", "2015년생"),
        ("나이 미상, 검정 외투", ""),
    ],
)
def test_age_variants_used_in_alerts(text, expected):
    assert extract_age(text) == expected
    assert enhance_features_from_text({}, text, "").get("age", "") == expected


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("남 66세, 노란 우비, 검정 장화, 투명 우산", "outerwear", "우비"),
        ("여 75세, 꽃무늬 앞치마, 자주색 긴팔티", "outerwear", "앞치마"),
        ("남 58세, 얼룩무늬 군복 상의, 군복 바지, 전투화", "top", "군복"),
        ("남 58세, 얼룩무늬 군복 상의, 군복 바지, 전투화", "shoes", "전투화"),
        ("여 69세, 짧은 웨이브머리, 두꺼운 검정테 안경", "hair_texture", "웨이브"),
        ("여 69세, 짧은 웨이브머리, 두꺼운 검정테 안경", "glasses", "검정테"),
        ("남 72세, 희끗희끗한 머리, 턱수염", "hair_color", "희끗희끗"),
        ("여 80세, 분홍 토시, 갈색 지팡이, 보행 보조기", "accessories", "보행 보조기"),
        ("남 63세, 청색 작업복, 고무장갑, 손수레", "accessories", "손수레"),
        ("여 11세, 흰색 레이스 블라우스, 남색 주름치마, 분홍 머리띠", "bottom", "주름치마"),
        ("여 11세, 흰색 레이스 블라우스, 남색 주름치마, 분홍 머리띠", "accessories", "머리띠"),
        ("남 32세, 검정 반팔 상의, 오른팔 문신, 왼쪽 눈 밑 점", "special_features", "오른팔 문신"),
        ("남 32세, 검정 반팔 상의, 오른팔 문신, 왼쪽 눈 밑 점", "special_features", "왼쪽 눈 밑 점"),
    ],
)
def test_more_unseen_real_world_details(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("남 79세, 연회색 내복, 검정 털신, 파란 목도리", "top", "내복"),
        ("남 79세, 연회색 내복, 검정 털신, 파란 목도리", "accessories", "목도리"),
        ("여 67세, 빨간 몸빼바지, 꽃무늬 버선, 흰 두건", "shoes", "버선"),
        ("여 67세, 빨간 몸빼바지, 꽃무늬 버선, 흰 두건", "hat_type", "두건"),
        ("남 54세, 형광 안전조끼, 파란 작업복, 노란 안전모", "outerwear", "안전조끼"),
        ("남 54세, 형광 안전조끼, 파란 작업복, 노란 안전모", "top", "파란색 작업복"),
        ("남 54세, 형광 안전조끼, 파란 작업복, 노란 안전모", "hat_type", "안전모"),
        ("여 73세, 보라색 스카프, 갈색 핸드백, 검정 돋보기안경", "accessories", "스카프"),
        ("여 73세, 보라색 스카프, 갈색 핸드백, 검정 돋보기안경", "glasses", "돋보기안경"),
        ("남 82세, 환자복, 병원 슬리퍼, 팔에 링거 바늘", "top", "환자복"),
        ("남 82세, 환자복, 병원 슬리퍼, 팔에 링거 바늘", "special_features", "링거"),
        ("남 45세, 검정 오토바이 헬멧, 회색 배달조끼, 청바지", "hat_type", "헬멧"),
        ("여 10세, 노란 레인부츠, 빨간 책가방, 양갈래 머리", "shoes", "레인부츠"),
        ("남 68세, 흰 런닝셔츠, 남색 잠옷바지, 맨발", "top", "런닝셔츠"),
        ("남 68세, 흰 런닝셔츠, 남색 잠옷바지, 맨발", "shoes", "맨발"),
    ],
)
def test_additional_field_report_vocabulary(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("실종 남 76세 168센티 60킬로 검정잠바", "height", "168cm"),
        ("실종 남 76세 168센티 60킬로 검정잠바", "weight", "60kg"),
        ("여 83세, 빨강 상의, 검정 하의", "top", "빨간색 상의"),
        ("남 14세, 검정 트레이닝바지, 흰 하이탑 운동화", "bottom", "트레이닝바지"),
        ("남 14세, 검정 트레이닝바지, 흰 하이탑 운동화", "shoes", "하이탑 운동화"),
        ("여 62세, 파란 체크무늬 원피스, 베이지 숄", "outerwear", "숄"),
        ("남 71세, 남색 깔깔이, 회색 면바지", "outerwear", "깔깔이"),
        ("여 78세, 꽃무늬 일바지, 자주색 조끼", "bottom", "일바지"),
        ("남 39세, 주황색 조끼, 검정 방수바지, 헤드랜턴", "bottom", "방수바지"),
        ("남 39세, 주황색 조끼, 검정 방수바지, 헤드랜턴", "accessories", "헤드랜턴"),
        ("여 6세, 분홍 패딩조끼, 흰 타이즈", "outerwear", "패딩조끼"),
        ("여 6세, 분홍 패딩조끼, 흰 타이즈", "bottom", "타이즈"),
        ("남 80세, 회색 마고자, 흰 저고리", "outerwear", "마고자"),
        ("남 80세, 회색 마고자, 흰 저고리", "top", "저고리"),
        ("여 74세, 선글라스, 갈색 숄더백", "glasses", "선글라스"),
        ("여 74세, 선글라스, 갈색 숄더백", "accessories", "숄더백"),
    ],
)
def test_compact_units_and_less_common_garments(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")


def test_shoulder_bag_is_not_misclassified_as_a_shawl():
    facts = enhance_features_from_text({}, "여 74세, 선글라스, 갈색 숄더백", "")
    assert facts["accessories"] == "갈색 숄더백"
    assert not facts.get("outerwear")


@pytest.mark.parametrize(
    "text,key,expected",
    [
        ("여 81세, 분홍 저고리, 남색 한복치마, 흰 버선, 은색 비녀", "bottom", "한복치마"),
        ("여 81세, 분홍 저고리, 남색 한복치마, 흰 버선, 은색 비녀", "accessories", "비녀"),
        ("남 77세, 회색 개량한복, 검정 고무신, 염주", "top", "개량한복"),
        ("남 77세, 회색 개량한복, 검정 고무신, 염주", "accessories", "염주"),
        ("여 68세, 자주색 누빔조끼, 꽃무늬 몸빼, 검정 덧신", "outerwear", "누빔조끼"),
        ("여 68세, 자주색 누빔조끼, 꽃무늬 몸빼, 검정 덧신", "shoes", "덧신"),
        ("남 84세, 환자복 상하의, 파란 병원팔찌, 흰 실내화", "accessories", "병원팔찌"),
        ("남 84세, 환자복 상하의, 파란 병원팔찌, 흰 실내화", "bottom", "환자복 바지"),
        ("여 72세, 검정 나팔바지, 장바구니카트", "bottom", "나팔바지"),
        ("여 72세, 검정 나팔바지, 장바구니카트", "accessories", "장바구니카트"),
        ("남 9세, 회색 조거팬츠, 초록 물통", "bottom", "조거팬츠"),
        ("남 9세, 회색 조거팬츠, 초록 물통", "accessories", "물통"),
        ("여 16세, 검정 후드, 청치마, 흰 캔버스화, 무선이어폰", "top", "후드"),
        ("여 16세, 검정 후드, 청치마, 흰 캔버스화, 무선이어폰", "shoes", "캔버스화"),
        ("여 16세, 검정 후드, 청치마, 흰 캔버스화, 무선이어폰", "accessories", "무선이어폰"),
        ("남 35세, 형광 작업조끼, 검정 등산바지, 등산스틱 2개", "accessories", "등산스틱 2개"),
        ("여 59세, 베이지 트렌치코트, 검정 롱스커트, 갈색 앵클부츠", "outerwear", "트렌치코트"),
        ("여 59세, 베이지 트렌치코트, 검정 롱스커트, 갈색 앵클부츠", "shoes", "앵클부츠"),
        ("남 70세, 남색 골프웨어, 베이지 골프바지, 흰 골프화, 선캡", "hat_type", "선캡"),
    ],
)
def test_traditional_clothes_and_field_possessions(text, key, expected):
    facts = enhance_features_from_text({}, text, "")
    assert expected in facts.get(key, "")
