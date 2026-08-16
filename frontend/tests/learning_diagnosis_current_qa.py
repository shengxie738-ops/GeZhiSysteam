from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "learning-diagnosis-qa-current"
OUT.mkdir(parents=True, exist_ok=True)


def run_viewport(width: int, height: int, token: str):
    errors, page_errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.add_init_script(f"""
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('currentRole', 'student');
            localStorage.setItem('currentView', 'learning-diagnosis');
            localStorage.setItem('currentUser', JSON.stringify({{username:'23001020119', real_name:'婕旂ず瀛︾敓', student_id:'23001020119'}}));
            localStorage.setItem('apiOrigin', 'http://127.0.0.1:8516');
            localStorage.setItem('token', {token!r});
        """)
        page.goto("http://127.0.0.1:5174/", wait_until="networkidle", timeout=30000)
        page.locator("section h1").filter(has_text="编程学习诊断").last.wait_for(timeout=30000)
        page.locator("h2").filter(has_text="当前结论").wait_for(timeout=30000)
        page.locator("h2").filter(has_text="四阶段").wait_for(timeout=30000)
        page.screenshot(path=OUT / f"{width}x{height}-home.png", full_page=True)

        page.locator("button").filter(has_text="更换目标").click()
        page.locator("h2").filter(has_text="更换学习目标").wait_for(timeout=5000)
        page.screenshot(path=OUT / f"{width}x{height}-goal.png", full_page=True)
        page.locator("button").filter(has_text="取消").click()

        page.locator("button").filter(has_text="查看证据").click()
        page.locator("h2").filter(has_text="诊断证据").wait_for(timeout=5000)
        page.screenshot(path=OUT / f"{width}x{height}-evidence.png", full_page=True)
        page.locator("div.fixed.inset-0").last.locator("button").first.click()

        page.locator("button").filter(has_text="纳入 Git 证据").click()
        page.locator("h3").filter(has_text="确认纳入 Git 证据").wait_for(timeout=5000)
        page.screenshot(path=OUT / f"{width}x{height}-git-risk.png", full_page=True)
        page.locator("button").filter(has_text="暂不纳入").click()

        first_task = page.locator("button").filter(has_text="KNOWLEDGE_REVIEW").first
        if first_task.count():
            first_task.click()
            page.locator("p").filter(has_text="Learning diagnosis / Review").wait_for(timeout=5000)
            page.screenshot(path=OUT / f"{width}x{height}-task.png", full_page=True)
            page.locator("button").filter(has_text="返回学习诊断").click()

        layout = page.evaluate("""() => ({
            viewport: {w: innerWidth, h: innerHeight},
            document: {w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight},
            body: {w: document.body.scrollWidth, h: document.body.scrollHeight}
        })""")
        browser.close()
    return {"viewport": [width, height], "console_errors": errors, "page_errors": page_errors, "layout": layout}


def main():
    token = (ROOT / "artifacts" / "qa_token.txt").read_text(encoding="utf-8").strip()
    results = [run_viewport(1440, 1000, token), run_viewport(1366, 768, token)]
    print({"results": results, "output": str(OUT)})


if __name__ == "__main__":
    main()
