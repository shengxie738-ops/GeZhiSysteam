import os
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright


def history_payload(mode):
    data = [
        {
            "id": 101,
            "role": "user",
            "sender_id": None,
            "content": "rag question",
            "created_at": "2026-06-30 23:35:10",
        },
        {
            "id": 102,
            "role": "assistant",
            "sender_id": "agent_researcher",
            "content": "rag answer with citation",
            "created_at": "2026-06-30 23:35:25",
        },
    ]
    return {"status": "success", "data": data if mode == "rag" else []}


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    page.route(
        "**/api/chat/history**",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            json=history_payload(
                parse_qs(urlparse(route.request.url).query).get("agent_mode", ["tutor"])[0]
            ),
        ),
    )

    page.add_init_script(
        """
        localStorage.setItem('isLoggedIn', 'true');
        localStorage.setItem('currentRole', 'student');
        localStorage.setItem('currentView', 'workspace');
        localStorage.setItem('currentUser', JSON.stringify({ username: 'alice' }));
        """
    )

    base_url = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8088")
    page.goto(f"{base_url}/index.html", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)

    page.locator("text=DataBot").click()
    expect(page.locator(".knowledge-search-shell")).to_be_visible(timeout=5000)
    expect(page.locator(".knowledge-history-rail")).to_be_visible()
    expect(page.locator("text=检索核心概念")).to_be_visible()

    chat_box = page.locator(".knowledge-search-shell").bounding_box()
    rail_box = page.locator(".knowledge-history-rail").bounding_box()
    assert chat_box and rail_box, "knowledge workspace panels should have measurable boxes"
    assert rail_box["x"] > chat_box["x"] + chat_box["width"] - 2, "history rail should sit to the right of chat shell"
    assert rail_box["height"] > 500, "history rail should be tall enough to read records"

    os.makedirs("test-artifacts", exist_ok=True)
    page.screenshot(path="test-artifacts/knowledge-workspace-rag.png", full_page=True)

    assert not errors, "\n".join(errors)
    browser.close()
