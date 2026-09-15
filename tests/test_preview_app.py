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
    assert "흰색 외투 (브랜드: 정보 없음)" in rendered
    assert "서울역" in rendered
    assert len(calls) == 3  # one extraction, one image, one vision check
