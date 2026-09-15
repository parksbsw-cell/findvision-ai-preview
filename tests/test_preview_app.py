import base64
import json
from pathlib import Path

import requests
from streamlit.testing.v1 import AppTest


class FakeResponse:
    status_code = 200
    ok = True

    def __init__(self, result):
        self.result = result

    def json(self):
        return {"success": True, "result": self.result}


def test_fast_preview_keeps_original_and_shows_outerwear(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    calls = []
    one_pixel_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        "AAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=="
    )

    def fake_post(url, **kwargs):
        calls.append(url)
        if "llama-3.1" in url:
            return FakeResponse(
                {
                    "response": {
                        "name": "",
                        "gender": "남성",
                        "age": "68세",
                        "body_type": "마른 편",
                        "top": "빨간 반팔티",
                        "outerwear": "흰색 외투",
                        "outerwear_brand": "",
                        "bottom": "검은 긴바지",
                        "shoes": "검은 크록스",
                        "last_seen_location": "서울역",
                        "image_prompt_en": (
                            "an older man in a red T-shirt under an open white coat, "
                            "black pants and black clogs"
                        ),
                        "verification_requirements_en": (
                            "open white coat over red T-shirt; black pants; black clogs"
                        ),
                    }
                }
            )
        if "flux-2-klein" in url:
            return FakeResponse({"image": base64.b64encode(one_pixel_png).decode()})
        if "moondream" in url:
            return FakeResponse(
                {
                    "answer": json.dumps(
                        {
                            "score": 90,
                            "pass": True,
                            "missing": [],
                            "wrong": [],
                            "has_text": False,
                            "feedback_en": "",
                        }
                    )
                }
            )
        raise AssertionError(f"Unexpected API: {url}")

    monkeypatch.setattr(requests, "post", fake_post)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
    assert not app.exception
    assert len(app.text_area) == 2
    app.text_area[0].set_value("원문: 남성, 빨간 반팔티, 검은 긴바지")
    app.text_area[1].set_value("추가: 흰색 외투, 서울역 마지막 목격")
    app.button[0].click().run()

    assert not app.exception
    assert app.metric[0].value == "1회"
    rendered = "\n".join(markdown.value for markdown in app.markdown)
    assert "마른 편" in rendered
    assert "흰색 외투 (브랜드: 정보 없음)" in rendered
    assert "겉옷 여밈" not in rendered
    assert "서울역" in rendered
    assert any(button.label == "다시 생성하기" for button in app.button)
    assert len(calls) == 3  # one extraction, one image, one vision check


def test_unmentioned_outerwear_is_not_required_by_generation_or_vision(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    prompts = {}
    one_pixel_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        "AAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=="
    )

    def fake_post(url, **kwargs):
        if "llama-3.1" in url:
            prompts["extraction"] = kwargs["json"]["messages"][0]["content"]
            return FakeResponse(
                {
                    "response": {
                        "gender": "남성",
                        "top": "빨간 반팔티",
                        "bottom": "검은 긴바지",
                        "shoes": "검은 크록스",
                        "image_prompt_en": "a man in a red T-shirt, black pants and black clogs",
                        "verification_requirements_en": (
                            "red T-shirt; black pants; black clogs"
                        ),
                    }
                }
            )
        if "flux-2-klein" in url:
            prompts["generation"] = kwargs["files"]["prompt"][1]
            return FakeResponse({"image": base64.b64encode(one_pixel_png).decode()})
        if "moondream" in url:
            prompts["vision"] = kwargs["json"]["question"]
            return FakeResponse(
                {
                    "answer": json.dumps(
                        {"score": 90, "pass": True, "missing": [], "wrong": []}
                    )
                }
            )
        raise AssertionError(f"Unexpected API: {url}")

    monkeypatch.setattr(requests, "post", fake_post)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=10).run()
    app.text_area[0].set_value("가상 예시: 남성, 빨간 반팔티, 검은 긴바지, 검은 크록스")
    app.button[0].click().run()

    assert not app.exception
    assert "겉옷이 명시된 경우에만" in prompts["extraction"]
    assert "No outerwear is specified" in prompts["generation"]
    assert "The stated outerwear must" not in prompts["generation"]
    assert "do not require a coat or jacket" in prompts["vision"]
    assert "required outerwear type/color/layer" not in prompts["vision"]
