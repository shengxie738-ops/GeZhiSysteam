import os
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright


def history_payload(mode):
    if mode == "rag":
        return {
            "status": "success",
            "data": [
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
                    "content": "rag answer",
                    "created_at": "2026-06-30 23:35:25",
                },
            ],
        }
    return {
        "status": "success",
        "data": [
            {
                "id": 201,
                "role": "user",
                "sender_id": None,
                "content": "tutor question",
                "created_at": "2026-06-30 23:34:10",
            }
        ],
    }


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
    expect(page.locator("text=检索历史")).to_be_visible()
    expect(page.locator("text=历史条目")).to_be_visible()
    expect(page.locator("text=rag question").first).to_be_visible(timeout=5000)
    expect(page.locator("text=2026-06-30 23:35:10").first).to_be_visible()

    page.locator("button[title]").first.click()
    page.locator("text=Alina").click()
    expect(page.locator("text=tutor question")).to_be_visible(timeout=5000)
    expect(page.locator("text=rag question")).not_to_be_visible()

    assert not errors, "\\n".join(errors)
    browser.close()
