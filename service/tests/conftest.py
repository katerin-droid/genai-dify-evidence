import httpx
import pytest

@pytest.fixture(autouse=True)
def forbid_real_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Real HTTP is forbidden in default pytest")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked)
