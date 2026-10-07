import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api import provider, server  # noqa: E402


def test_api_requires_the_team_connection_code(monkeypatch):
    monkeypatch.setenv("MOBILE_ACCESS_KEY", "a-connection-code-that-is-long-enough")
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/session",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "scheme": "http",
    }
    request = Request(scope)

    async def invoke():
        async def call_next(_request):
            raise AssertionError("unauthorized requests must not reach the handler")
        return await server.protect(request, call_next)

    response = asyncio.run(invoke())

    assert response.status_code == 401


def test_sparse_alert_can_start_generation(monkeypatch, tmp_path):
    monkeypatch.setenv("MOBILE_ACCESS_KEY", "a-connection-code-that-is-long-enough")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://testserver")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    monkeypatch.setattr(server, "DB", str(tmp_path / "usage.sqlite3"))
    submitted = []

    def submit(function, *args):
        submitted.append(args)
        server.slots.release()

    monkeypatch.setattr(server.pool, "submit", submit)
    request = SimpleNamespace(state=SimpleNamespace(owner="test-owner"), client=None)
    response = server.start(server.Generation(features={}, mode="fast"), request)

    assert response["id"]
    assert submitted
    assert provider.build_generation_prompt({}, "")


def test_sparse_prompt_uses_korean_default_without_inventing_location():
    prompt = provider.build_generation_prompt(
        {"last_seen_location": "서울역", "alert_area": "서울"}, ""
    )

    assert "Korean" in prompt
    assert "plain, unbranded" in prompt
    assert "서울역" not in prompt
    assert "alert area" not in prompt.lower()


def test_visits_increment_per_session_not_per_generation(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "DB", str(tmp_path / "visits.sqlite3"))
    clock = [1000.0]
    monkeypatch.setattr(server.time, "time", lambda: clock[0])

    assert server.record_visit("anonymous-device") == 1
    clock[0] += 60
    assert server.record_visit("anonymous-device") == 1
    clock[0] += 1800
    assert server.record_visit("anonymous-device") == 2
