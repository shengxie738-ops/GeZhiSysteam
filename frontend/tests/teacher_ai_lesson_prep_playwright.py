from pathlib import Path
import os

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "artifacts" / "teacher-ai-lesson-prep-qa"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    token = os.environ["QA_TEACHER_TOKEN"]
    frontend_url = os.getenv("QA_FRONTEND_URL", "http://127.0.0.1:5174")
    api_origin = os.getenv("QA_API_ORIGIN", "http://127.0.0.1:8516")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page = context.new_page()
        console_errors = []
        page_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.add_init_script("""
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('currentRole', 'teacher');
            localStorage.setItem('currentView', 't_lesson_prep');
            localStorage.setItem('currentUser', JSON.stringify({username:'qa-teacher', real_name:'验收教师'}));
            localStorage.setItem('apiOrigin', %r);
            localStorage.setItem('token', %r);
        """ % (api_origin, token))
        def isolate_unrelated_api(route):
            if "/api/teacher/lesson-prep/" in route.request.url:
                route.continue_()
            else:
                route.fulfill(json={"code": 200, "message": "ok", "data": {}})

        page.route(f"{api_origin}/api/**", isolate_unrelated_api)
        page.goto(frontend_url, wait_until="networkidle", timeout=30000)
        try:
            page.wait_for_selector('[data-testid="teacher-ai-lesson-prep"]', timeout=15000)
        except Exception:
            page.screenshot(path=OUT / "failure-state.png", full_page=True)
            print({
                "url": page.url,
                "storage": page.evaluate("Object.fromEntries(Object.entries(localStorage))"),
                "body": page.locator("body").inner_text()[:500],
                "console_errors": console_errors,
                "page_errors": page_errors,
            })
            raise
        page.wait_for_function("document.querySelector('[data-testid=lesson-prep-resource-total]')?.textContent.includes('97')", timeout=15000)
        page.screenshot(path=OUT / "01-teacher-ai-lesson-prep.png", full_page=True)
        layout = page.evaluate("""() => ({
          viewportWidth: innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          sidebarEntry: [...document.querySelectorAll('button')].some((item) => item.querySelector('.ph-notebook')),
          workspaceVisible: Boolean(document.querySelector('[data-testid=teacher-ai-lesson-prep]'))
        })""")
        print({"console_errors": console_errors, "page_errors": page_errors, "layout": layout, "output": str(OUT)})
        browser.close()


if __name__ == "__main__":
    main()
