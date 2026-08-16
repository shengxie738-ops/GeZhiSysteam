import os

from playwright.sync_api import expect, sync_playwright


base_url = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8088/index.html")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 2048, "height": 1024})
    page.add_init_script(
        """
        localStorage.setItem('isLoggedIn', 'true');
        localStorage.setItem('currentRole', 'student');
        localStorage.setItem('currentView', 'coding');
        localStorage.setItem('currentUser', JSON.stringify({
            username: '李明',
            role: 'student'
        }));
        """
    )
    page.goto(base_url)
    page.wait_for_load_state("networkidle")

    expect(page.get_by_text("竞技排位赛").first).to_be_visible(timeout=10000)
    page.get_by_text("参加排位赛").click()

    expect(page.get_by_text("王者之路，由此启程")).to_be_visible(timeout=10000)
    expect(page.get_by_text("进入竞技答题舱")).to_be_visible()
    expect(page.locator("h3").filter(has_text="每日挑战")).to_be_visible()
    expect(page.get_by_role("heading", name="排行榜")).to_be_visible()
    page.screenshot(path="test-artifacts/coding-ranked-lobby.png", full_page=True)

    page.get_by_text("开始匹配").first.click()
    page.wait_for_timeout(1200)
    expect(page.get_by_text("排位 AI 教练")).to_be_visible(timeout=10000)
    page.screenshot(path="test-artifacts/coding-ranked-coach.png", full_page=True)

    page.get_by_test_id("ranked-tab-history").click()
    expect(page.get_by_text("每一场对决，皆是段位的注脚")).to_be_visible(timeout=10000)
    expect(page.get_by_text("Cache 组相联命中模拟")).to_be_visible()
    page.screenshot(path="test-artifacts/coding-ranked-history.png", full_page=True)

    page.get_by_test_id("ranked-tab-mistakes").click()
    expect(page.get_by_text("直面错题，方能登顶")).to_be_visible(timeout=10000)
    expect(page.get_by_text("岛屿数量")).to_be_visible()
    page.screenshot(path="test-artifacts/coding-ranked-mistakes.png", full_page=True)

    page.get_by_test_id("ranked-tab-season").click()
    expect(page.get_by_text("一个学期，一段王者征程")).to_be_visible(timeout=10000)
    expect(page.get_by_text("2026 春季学期")).to_be_visible()

    page.screenshot(path="test-artifacts/coding-ranked-season.png", full_page=True)
    browser.close()

print("coding ranked page browser check passed")
