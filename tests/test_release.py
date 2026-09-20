import base64
import json
from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

from preview_logic import category_text, enhance_features_from_text

APP = Path(__file__).resolve().parents[1] / "app.py"
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=="


class Response:
    ok = True
    status_code = 200

    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data

    def raise_for_status(self):
        pass


def setup_app(monkeypatch, *, precise=False, vision_error=False, fail_second=False, analytics=False):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "never-display-this-secret")
    if analytics:
        monkeypatch.setenv("CLUESIGHT_ANALYTICS_ENABLED", "true")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        if "cluesight_events" in url:
            return Response({})
        if "llama" in url:
            return Response({"success": True, "result": {"response": {
                "gender": "남성", "age": "20", "hair_style": "투블럭",
                "top": "검은색 나이키 반팔티", "top_brand": "Nike",
                "shoes_brand": "Nike", "bottom": "파란색 청바지", "shoes": "흰색 운동화",
                "last_seen_location": "서울역", "alert_area": "서울역",
                "image_prompt_en": "a person at Seoul Station", "verification_requirements_en": "Seoul Station"
            }}})
        if "flux" in url:
            if fail_second and sum("flux" in u for u, _ in calls) == 2:
                raise requests.Timeout("never-display-this-secret")
            return Response({"success": True, "result": {"image": PNG}})
        if vision_error:
            raise requests.Timeout("never-display-this-secret")
        return Response({"success": True, "result": {"answer": json.dumps({
            "score": 60 if precise else 90, "pass": not precise,
            "missing": ["shirt"] if precise else [], "wrong": [], "has_text": False,
            "feedback_en": "Correct the shirt color."
        })}})

    monkeypatch.setattr(requests, "post", post)
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.text_area[0].set_value("20세 남성, 검은색 나이키 반팔티, 파란색 청바지, 흰색 운동화, 투블럭, 마지막 목격 위치 서울역")
    if precise:
        app.radio[0].set_value("정밀 생성")
    app.button[0].click().run()
    return app, calls


def test_retry_survives_reruns_without_duplicate_count(monkeypatch):
    app, calls = setup_app(monkeypatch)
    assert not app.exception
    assert app.metric[0].value == "1회"
    app.run()
    assert len(calls) == 3
    assert app.metric[0].value == "1회"
    next(b for b in app.button if b.label == "다시 생성하기").click().run()
    assert not app.exception
    assert app.metric[0].value == "2회"
    assert len(calls) == 6
    prompt = next(k["files"]["prompt"][1] for u, k in calls if "flux" in u)
    assert "서울역" not in prompt and "Seoul Station" not in prompt
    assert "two-block" in prompt and "jeans" in prompt


@pytest.mark.parametrize("vision_error,fail_second,expected", [(False, False, 3), (True, False, 1), (False, True, 2)])
def test_precise_attempt_limits_and_partial_result(monkeypatch, vision_error, fail_second, expected):
    app, calls = setup_app(monkeypatch, precise=True, vision_error=vision_error, fail_second=fail_second)
    assert not app.exception
    assert app.metric[0].value == "1회"
    assert sum("flux" in u for u, _ in calls) == expected
    assert app.session_state["last_result"]["best"]["image"] == base64.b64decode(PNG)
    assert "never-display-this-secret" not in str(app.error)
    image_call = next(k for u, k in calls if "flux" in u)
    assert image_call["files"]["width"][1] == "768"


def test_analytics_is_private_and_emitted_once_per_result(monkeypatch):
    app, calls = setup_app(monkeypatch, analytics=True)
    events = [(u, k) for u, k in calls if "cluesight_events" in u]
    assert len(events) == 1
    payload = events[0][1]["json"]
    assert payload["attempts"] == 1
    assert payload["total_seconds"] >= payload["first_image_seconds"] >= 0
    assert not {"message", "image", "name", "last_seen_location"} & payload.keys()
    assert "Authorization" not in events[0][1]["headers"]
    app.run()
    assert sum("cluesight_events" in u for u, _ in calls) == 1


def test_explicit_brand_and_region_override_model_hallucination():
    facts = enhance_features_from_text({"shoes_brand": "Nike", "alert_area": "서울역"},
                                      "검은색 나이키 반팔티, 흰색 운동화, 마지막 목격 위치 서울역", "")
    assert facts["top_brand"] == "나이키"
    assert not facts["shoes_brand"]
    assert not facts["alert_area"]
    assert category_text(facts, "top") == "검은색 반팔티 (나이키)"


@pytest.mark.parametrize("style", ["투블럭", "버섯머리", "장발", "단발", "울프컷", "히피펌", "가르마펌", "반삭", "삭발"])
def test_korean_hairstyles_are_explicit(style):
    facts = enhance_features_from_text({}, f"검은색 반팔티, {style}", "")
    assert facts["hair_style"] == style


@pytest.mark.parametrize("body", ["마른 편", "저체중", "통통한 편", "뚱뚱한 편", "비만", "고도 비만", "보통 체형"])
def test_body_shape_is_not_inferred_from_weight(body):
    assert enhance_features_from_text({}, body, "")["body_type"] == body
    assert not enhance_features_from_text({"body_type": "비만"}, "몸무게 120kg", "")["body_type"]


def test_flagged_response_stops_without_retry_or_secret_output(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "private-value")
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        if "llama" in url:
            return Response({"success": True, "result": {"response": {
                "top": "검은색 반팔티", "bottom": "청바지", "shoes": "운동화"
            }}})
        response = Response({"success": False, "errors": [{"message": "Your output has been flagged private-value"}]})
        response.ok = False
        response.status_code = 400
        return response

    monkeypatch.setattr(requests, "post", post)
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.text_area[0].set_value("검은색 반팔티, 청바지, 운동화")
    app.radio[0].set_value("정밀 생성")
    app.button[0].click().run()
    assert len(calls) == 2
    assert app.metric[0].value == "0회"
    assert "안전 검사" in app.error[0].value
    assert "private-value" not in app.error[0].value
    assert any(b.label == "다시 생성하기" for b in app.button)
