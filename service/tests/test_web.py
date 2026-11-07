from pathlib import Path
import socket
import sys
import threading
import time
import pytest
import uvicorn
from fastapi.testclient import TestClient
from service.app.main import create_app
from service.app.config import Settings

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ["bigfish/bigfish_main.jpg", "bigfish/bigfish_self_comfort.jpg", "bigfish/bigfish_busy.webp", "nailong/nailong_face.jpg", "nailong/nailong_wait.jpg", "nailong/nailong_look.jpg", "gugugaga/gugugaga_smirk.jpg", "gugugaga/gugugaga_thumbsup.webp", "gugugaga/gugugaga_sideeye.jpg", "gugugaga/gugugaga_salute.jpg"]

@pytest.mark.parametrize("asset", ASSETS)
def test_user_image_routes(asset):
    if not (ROOT / "web/assets/mascots" / asset).is_file():
        pytest.skip("User image not supplied; redistribution rights pending")
    with TestClient(create_app(Settings())) as client:
        r = client.get("/static/assets/mascots/" + asset)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/")


def test_static_and_disconnected_status():
    with TestClient(create_app(Settings())) as client:
        assert "课程资料侦探社" in client.get("/").text
        status = client.get("/api/ui-status").json()
        assert not status["chat_available"] and not status["dify_connected"]
        assert "服务尚未连接" in status["message"]
        assert client.get("/static/.env").status_code == 404
        assert client.get("/.env").status_code == 404
        for path in ["/static/app.js", "/static/style.css", "/api/ui-status"]:
            body = client.get(path).text
            assert "sk-" not in body and "DEEPSEEK_API_KEY" not in body and "DIFY_API_KEY" not in body


def test_browser_interactions_and_screenshots():
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    if not all((ROOT / "web/assets/mascots" / a).is_file() for a in ASSETS):
        pytest.skip("Local user images required")
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(Settings()), log_level="critical", access_log=False))
    t = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    t.start()
    out = ROOT / "artifacts/ui"
    out.mkdir(parents=True, exist_ok=True)
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(.05)
        assert server.started
        with sync_playwright() as p:
            browser = p.chromium.launch(**({"channel": "msedge"} if sys.platform == "win32" else {}), headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1100}, permissions=["clipboard-read", "clipboard-write"])
            page = context.new_page()
            requests = []
            page.on("request", lambda r: requests.append((r.method, r.url)))
            page.goto(f"http://127.0.0.1:{port}")
            page.wait_for_function("Array.from(document.querySelectorAll('img[data-image]')).every(i=>i.complete&&i.naturalWidth>0)")
            assert page.locator("#submit").is_disabled()
            assert "服务尚未连接" in page.locator("#connection").inner_text()
            page.screenshot(path=str(out / "home-desktop.png"), full_page=True)
            page.locator("#demo").click()
            page.locator("[data-question]").first.click()
            assert page.locator("#question").input_value()
            page.locator("#submit").click()
            page.wait_for_timeout(160)
            assert "正在捞取" in page.locator("#wait-text").inner_text()
            page.screenshot(path=str(out / "waiting-fish.png"), full_page=True)
            page.wait_for_timeout(800)
            assert "先别急" in page.locator("#wait-text").inner_text()
            page.screenshot(path=str(out / "waiting-nailong.png"), full_page=True)
            page.wait_for_timeout(750)
            assert "核对证据" in page.locator("#wait-text").inner_text()
            page.screenshot(path=str(out / "waiting-evidence.png"), full_page=True)
            page.locator(".summary.supported").wait_for()
            assert "奶龙认证" in page.locator("#summary").inner_text()
            page.locator("#expand").click()
            assert page.locator("details").first.get_attribute("open") is not None
            assert "本课程共12周。" in page.locator("blockquote").inner_text()
            page.locator("#copy").click()
            page.wait_for_timeout(100)
            report = page.evaluate("navigator.clipboard.readText()")
            assert "示例数据，非真实模型结果" in report and "supported" in report
            page.screenshot(path=str(out / "supported-fun.png"), full_page=True)
            page.locator("#tone").click()
            assert page.locator(".mascot:visible").count() == 0
            page.locator("#copy").click()
            page.wait_for_timeout(100)
            assert page.evaluate("navigator.clipboard.readText()") == report
            page.screenshot(path=str(out / "supported-serious.png"), full_page=True)
            page.locator("#tone").click()
            for status in ["partially_supported", "unsupported", "verification_failed"]:
                page.locator("#scenario").select_option(status)
                page.locator("#submit").click()
                page.locator(".summary." + status).wait_for()
                assert page.locator("#demo-label").is_visible()
                if status == "verification_failed":
                    assert page.locator(".summary.unsupported").count() == 0
                    assert "example_timeout" in page.locator("#summary").inner_text()
                page.screenshot(path=str(out / (status + ".png")), full_page=True)
            page.locator("#reset").click()
            assert page.locator("#question").input_value() == ""
            page.locator("#real").click()
            assert page.locator("#result").is_hidden() and page.locator("#submit").is_disabled()
            page.locator(".photo img").click()
            assert page.locator("#toast").is_visible()
            page.route("**/bigfish_main.jpg", lambda route: route.abort())
            page.reload()
            page.locator(".photo .fallback").wait_for()
            page.screenshot(path=str(out / "image-fallback.png"), full_page=True)
            page.unroute("**/bigfish_main.jpg")
            page.set_viewport_size({"width": 390, "height": 844})
            page.reload()
            page.wait_for_function("document.querySelector('.photo img').naturalWidth>0")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(out / "home-mobile.png"), full_page=True)
            assert not any(method == "POST" for method, url in requests)
            assert all(url.startswith(f"http://127.0.0.1:{port}") for method, url in requests)
            browser.close()
    finally:
        server.should_exit = True
        t.join(10)
        sock.close()
        assert not t.is_alive()
