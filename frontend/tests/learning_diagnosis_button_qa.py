from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    token = (ROOT.parent / "artifacts" / "qa_token.txt").read_text(encoding="utf-8").strip()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        console_errors, page_errors, failed = [], [], []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("requestfailed", lambda req: failed.append({"url": req.url, "error": req.failure}))
        page.add_init_script(f"""
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('currentRole', 'student');
            localStorage.setItem('currentView', 'learning-diagnosis');
            localStorage.setItem('currentUser', JSON.stringify({{username:'23001020119', real_name:'测试学生', student_id:'23001020119'}}));
            localStorage.setItem('apiOrigin', 'http://127.0.0.1:8516');
            localStorage.setItem('token', {token!r});
        """)
        page.goto("http://127.0.0.1:5174/", wait_until="networkidle", timeout=30000)
        page.locator("h2").filter(has_text="四阶段").wait_for(timeout=30000)
        task = page.locator("button").filter(has_text="KNOWLEDGE_REVIEW").first
        task.click()
        page.get_by_text("获取提示").click()
        page.wait_for_timeout(1500)
        print({"console_errors": console_errors, "page_errors": page_errors, "failed": failed})
        browser.close()


if __name__ == "__main__":
    main()
