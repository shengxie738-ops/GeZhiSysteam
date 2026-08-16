from pathlib import Path
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "artifacts" / "learning-diagnosis-qa"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    token = (ROOT.parent / "artifacts" / "qa_token.txt").read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.add_init_script("""
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('currentRole', 'student');
            localStorage.setItem('currentView', 'learning-diagnosis');
            localStorage.setItem('currentUser', JSON.stringify({username:'story-student', real_name:'演示学生', student_id:'story-student'}));
            localStorage.setItem('apiOrigin', 'http://127.0.0.1:8516');
            localStorage.setItem('token', %r);
        """ % token)
        page.goto("http://127.0.0.1:5174/", wait_until="networkidle", timeout=30000)
        page.wait_for_selector("text=编程学习诊断", timeout=15000)
        page.screenshot(path=OUT / "01-home-empty.png", full_page=True)

        page.get_by_text("纳入 Git 项目代码").locator("xpath=..//button").click()
        page.wait_for_selector("text=确认纳入 Git 证据？")
        page.screenshot(path=OUT / "02-git-risk-modal.png", full_page=True)
        page.get_by_text("暂不纳入").click()

        page.get_by_text("开始诊断", exact=True).click()
        page.wait_for_selector("text=今日学习路径", timeout=30000)
        page.screenshot(path=OUT / "03-home-session.png", full_page=True)

        page.get_by_text("查看证据来源", exact=True).click()
        page.wait_for_selector("text=诊断证据与来源")
        page.screenshot(path=OUT / "04-evidence-modal.png", full_page=True)
        page.locator("div.fixed.inset-0").last.locator("button").first.click()

        page.locator("button").filter(has_text="CODING_PRACTICE").first.click()
        page.wait_for_selector("text=Python 沙箱")
        page.screenshot(path=OUT / "05-task-page.png", full_page=True)
        page.get_by_text("返回学习诊断").click()

        page.get_by_text("查看路径版本", exact=True).click()
        page.wait_for_selector("text=动态学习路径")
        page.screenshot(path=OUT / "06-version-page.png", full_page=True)

        layout = page.evaluate("""() => ({
          viewport: {w: innerWidth, h: innerHeight},
          document: {w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight},
          body: {w: document.body.scrollWidth, h: document.body.scrollHeight}
        })""")
        print({"console_errors": console_errors, "page_errors": page_errors, "layout": layout, "output": str(OUT)})
        browser.close()


if __name__ == "__main__":
    main()
