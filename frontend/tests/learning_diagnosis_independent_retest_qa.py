from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "artifacts" / "learning-diagnosis-independent-retest-qa"
OUT.mkdir(parents=True, exist_ok=True)
STUDENT_ID = "23001020119"


def main():
    with sync_playwright() as p:
        api = p.request.new_context(base_url="http://127.0.0.1:8516")
        login = api.post("/api/student/login", data={"username": STUDENT_ID, "password": "123456", "role": "student"})
        assert login.ok, login.text()
        token = login.json()["data"]["token"]
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        console_errors, page_errors, failed, bad = [], [], [], []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("requestfailed", lambda req: failed.append(req.url))
        page.on("response", lambda response: bad.append((response.url, response.status)) if response.status >= 400 else None)
        page.add_init_script(f"""
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('currentRole', 'student');
            localStorage.setItem('currentView', 'learning-diagnosis');
            localStorage.setItem('currentUser', JSON.stringify({{username:'{STUDENT_ID}', real_name:'演示学生', student_id:'{STUDENT_ID}'}}));
            localStorage.setItem('apiOrigin', 'http://127.0.0.1:8516');
            localStorage.setItem('token', {token!r});
        """)
        page.goto("http://127.0.0.1:5174/", wait_until="networkidle", timeout=30000)
        task_type_label = page.get_by_text("INDEPENDENT_RETEST", exact=False).last
        task_type_label.wait_for(timeout=30000)
        task_type_label.locator("xpath=ancestor::button").click()
        page.locator('[data-testid="independent-retest-page"]').wait_for(timeout=30000)
        page.get_by_label("learning-diagnosis-independent-retest-editor").wait_for()
        editor = page.get_by_label("learning-diagnosis-independent-retest-editor")
        editor.fill("print('wrong')")
        with page.expect_response(lambda r: r.url.endswith("/run") and r.request.method == "POST") as run_info:
            page.get_by_label("run-independent-retest").click()
        assert run_info.value.ok, run_info.value.text()
        assert run_info.value.json()["data"]["status"] == "TEST_FAILED"
        page.locator('[data-testid="independent-retest-page"]').wait_for()
        page.screenshot(path=OUT / "01-independent-failed.png", full_page=True)
        editor.fill("print(input())")
        with page.expect_response(lambda r: r.url.endswith("/run") and r.request.method == "POST") as pass_info:
            page.get_by_label("run-independent-retest").click()
        assert pass_info.value.ok, pass_info.value.text()
        assert pass_info.value.json()["data"]["status"] == "PASSED"
        page.locator('[data-testid="independent-retest-page"]').wait_for()
        page.screenshot(path=OUT / "02-independent-passed.png", full_page=True)
        page.set_viewport_size({"width": 1366, "height": 768})
        overflow = page.evaluate("({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth})")
        assert overflow["scrollWidth"] <= overflow["clientWidth"] + 1, overflow
        page.screenshot(path=OUT / "03-independent-1366x768.png", full_page=True)
        with page.expect_response(lambda r: r.url.endswith("/submit") and r.request.method == "POST") as submit_info:
            page.get_by_label("submit-independent-retest").click()
        assert submit_info.value.ok, submit_info.value.text()
        payload = submit_info.value.json()["data"]
        assert payload["execution"]["status"] == "PASSED"
        assert not console_errors, console_errors
        assert not page_errors, page_errors
        assert not failed, failed
        assert not bad, bad
        print({"status": "passed", "console_errors": console_errors, "page_errors": page_errors, "failed": failed, "bad": bad, "output": str(OUT)})
        browser.close()
        api.dispose()


if __name__ == "__main__":
    main()
