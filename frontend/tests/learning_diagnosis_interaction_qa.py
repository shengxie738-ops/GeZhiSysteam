from pathlib import Path
import re
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "artifacts" / "learning-diagnosis-qa-fixed"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    with sync_playwright() as p:
        api = p.request.new_context(base_url="http://127.0.0.1:8516")
        login = api.post("/api/student/login", data={
            "username": "23001020119",
            "password": "123456",
            "role": "student",
        })
        assert login.ok, f"演示账号登录失败: {login.status} {login.text()}"
        token = login.json()["data"]["token"]
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        console_errors, page_errors, failed = [], [], []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("requestfailed", lambda req: failed.append({"url": req.url, "failure": req.failure}))
        page.add_init_script(f"""
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('currentRole', 'student');
            localStorage.setItem('currentView', 'learning-diagnosis');
            localStorage.setItem('currentUser', JSON.stringify({{username:'23001020119', real_name:'演示学生', student_id:'23001020119'}}));
            localStorage.setItem('apiOrigin', 'http://127.0.0.1:8516');
            localStorage.setItem('token', {token!r});
        """)
        page.goto("http://127.0.0.1:5174/", wait_until="networkidle", timeout=30000)
        page.locator("h2").filter(has_text="当前结论").wait_for(timeout=30000)
        page.screenshot(path=OUT / "01-home-fixed.png", full_page=True)
        page.locator("button.metric-card").first.click()
        assert page.locator("button.metric-card.metric-expanded").count() == 1
        expanded_box = page.locator("button.metric-card.metric-expanded").bounding_box()
        assert expanded_box and expanded_box["width"] > 300
        page.screenshot(path=OUT / "02-metric-expanded.png", full_page=True)
        page.mouse.move(20, 20)
        page.wait_for_timeout(400)
        assert page.locator("button.metric-card.metric-expanded").count() == 0
        page.locator("button").filter(has_text="查看全部").click()
        page.screenshot(path=OUT / "03-evidence-detail.png", full_page=True)
        page.locator("div.fixed.inset-0").last.locator("button").first.click()

        page.get_by_role("button", name="查看版本变化").click()
        page.get_by_role("heading", name="版本记录").wait_for(timeout=30000)
        version_buttons = page.locator("aside button")
        assert version_buttons.count() >= 2, "演示数据至少需要两个路径版本"
        current_heading = page.get_by_role("heading", name=re.compile(r"动态学习路径 v\d+"))
        current_title = current_heading.inner_text()
        current_rows = page.locator("section.mt-3 article").count()
        page.screenshot(path=OUT / "04-version-history.png", full_page=True)

        version_buttons.last.click()
        page.wait_for_timeout(250)
        history_title = current_heading.inner_text()
        history_rows = page.locator("section.mt-3 article").count()
        assert history_title != current_title, "切换历史版本后版本标题应发生变化"
        assert history_rows != current_rows or page.get_by_text("历史版本", exact=True).count() == 1

        page.get_by_role("button", name=re.compile(r"^新增\s+\d+$")).click()
        added_rows = page.locator("section.mt-3 article")
        assert added_rows.count() > 0, "初始路径应包含新增任务"
        first_title = added_rows.first.locator("strong").inner_text().strip()
        search = page.get_by_placeholder("搜索任务或知识点")
        search.fill(first_title[:4])
        assert page.locator("section.mt-3 article").count() >= 1

        overflow = page.evaluate("({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth})")
        assert overflow["scrollWidth"] <= overflow["clientWidth"] + 1, f"页面发生横向溢出: {overflow}"

        page.set_viewport_size({"width": 1366, "height": 768})
        compact_overflow = page.evaluate("({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth})")
        assert compact_overflow["scrollWidth"] <= compact_overflow["clientWidth"] + 1, f"1366 宽度下页面发生横向溢出: {compact_overflow}"
        page.screenshot(path=OUT / "05-version-history-1366x768.png", full_page=True)
        page.get_by_role("button", name=re.compile(r"返回学习诊断")).click()
        page.get_by_role("heading", name="当前结论").wait_for(timeout=30000)
        page.locator("button").filter(has_text="KNOWLEDGE_REVIEW").first.click()
        page.get_by_text("获取提示").click()
        page.wait_for_timeout(1000)
        page.get_by_placeholder("写下你的知识点复述与例题分析").fill("链表操作需要先判断空链表与单节点，再更新前后指针并检查头尾节点边界。")
        page.get_by_text("我已完成复习").click()
        page.wait_for_timeout(1200)
        assert not console_errors, f"console errors: {console_errors}"
        assert not page_errors, f"page errors: {page_errors}"
        assert not failed, f"request failures: {failed}"
        print({"console_errors": console_errors, "page_errors": page_errors, "failed": failed, "output": str(OUT)})
        browser.close()
        api.dispose()


if __name__ == "__main__":
    main()
