from pathlib import Path
import re

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "artifacts" / "learning-diagnosis-coding-task-qa"
OUT.mkdir(parents=True, exist_ok=True)
STUDENT_ID = "23001020119"


def login(playwright):
    api = playwright.request.new_context(base_url="http://127.0.0.1:8516")
    response = api.post("/api/student/login", data={
        "username": STUDENT_ID,
        "password": "123456",
        "role": "student",
    })
    assert response.ok, f"演示账号登录失败: {response.status} {response.text()}"
    return api, response.json()["data"]["token"]


def latest(api, token):
    response = api.get(
        f"/api/learning-diagnosis/latest?student_id={STUDENT_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.ok, f"读取学习诊断失败: {response.status} {response.text()}"
    return response.json()["data"]


def assert_no_page_overflow(page):
    size = page.evaluate("({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth})")
    assert size["scrollWidth"] <= size["clientWidth"] + 1, f"页面发生横向溢出: {size}"


def main():
    with sync_playwright() as playwright:
        api, token = login(playwright)
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        console_errors, page_errors, failed, bad_responses = [], [], [], []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("requestfailed", lambda req: failed.append({"url": req.url, "failure": req.failure}))
        page.on("response", lambda response: bad_responses.append({"url": response.url, "status": response.status}) if response.status >= 400 else None)
        page.add_init_script(f"""
            localStorage.setItem('isLoggedIn', 'true');
            localStorage.setItem('currentRole', 'student');
            localStorage.setItem('currentView', 'learning-diagnosis');
            localStorage.setItem('currentUser', JSON.stringify({{username:'{STUDENT_ID}', real_name:'演示学生', student_id:'{STUDENT_ID}'}}));
            localStorage.setItem('apiOrigin', 'http://127.0.0.1:8516');
            localStorage.setItem('token', {token!r});
        """)

        before = latest(api, token)
        before_evidence = len(before.get("evidence") or [])
        before_version = int((before.get("snapshot") or {}).get("version") or 0)

        page.goto("http://127.0.0.1:5174/", wait_until="networkidle", timeout=30000)
        page.get_by_role("heading", name="当前结论").wait_for(timeout=30000)
        page.locator("button").filter(has_text="CODING_PRACTICE").first.click()
        editor = page.get_by_label("学习诊断代码编辑器")
        editor.wait_for(timeout=30000)
        page.get_by_text("Agent guide", exact=True).wait_for()
        assert page.get_by_role("button", name=re.compile("运行代码")).is_visible()
        assert page.get_by_role("button", name="提交并生成诊断").is_visible()

        failing_code = "print('wrong')"
        editor.fill(failing_code)
        with page.expect_response(lambda response: response.url.endswith("/run") and response.request.method == "POST", timeout=30000) as run_info:
            page.get_by_role("button", name=re.compile("运行代码")).click()
        assert run_info.value.ok, f"运行预览失败: {run_info.value.status} {run_info.value.text()}"
        failed_run_payload = run_info.value.json()["data"]
        assert failed_run_payload["status"] == "TEST_FAILED", failed_run_payload
        page.get_by_text(re.compile(r"^存在失败用例")).first.wait_for(timeout=30000)
        page.get_by_text(re.compile(r"0 / 3 通过")).wait_for()

        after_run = latest(api, token)
        assert len(after_run.get("evidence") or []) == before_evidence, "运行预览不得新增学习证据"
        assert int((after_run.get("snapshot") or {}).get("version") or 0) == before_version, "运行预览不得刷新诊断快照"

        with page.expect_response(lambda response: "/hints?" in response.url and response.request.method == "POST", timeout=30000) as hint_info:
            page.get_by_role("button", name="获取下一层提示").click()
        assert hint_info.value.ok, f"Hint 请求失败: {hint_info.value.status}"
        hint_request = hint_info.value.request.post_data_json
        assert hint_request["attempt"]["execution"]["status"] == "TEST_FAILED", "Hint 必须携带最近一次失败结果"
        page.get_by_text(re.compile(r"Level 1 / 5")).wait_for()
        assert_no_page_overflow(page)
        page.screenshot(path=OUT / "01-coding-failed-1440x1000.png", full_page=True)

        editor.fill("print('changed')")
        page.get_by_text("尚未运行", exact=True).wait_for()
        page.get_by_role("button", name="重置代码").click()
        assert "pass" in editor.input_value(), "重置代码应恢复 starter_code"
        passing_code = "print(input())"
        editor.fill(passing_code)
        with page.expect_response(lambda response: response.url.endswith("/run") and response.request.method == "POST", timeout=30000) as pass_run_info:
            page.get_by_role("button", name=re.compile("运行代码")).click()
        assert pass_run_info.value.ok, f"第二次运行预览失败: {pass_run_info.value.status}"
        run_payload = pass_run_info.value.json()["data"]
        assert run_payload["status"] == "PASSED", run_payload
        page.get_by_text(re.compile(r"^全部通过")).first.wait_for(timeout=30000)
        page.get_by_text(re.compile(r"3 / 3 通过")).wait_for()
        page.screenshot(path=OUT / "02-coding-passed-1440x1000.png", full_page=True)

        page.set_viewport_size({"width": 1366, "height": 768})
        assert_no_page_overflow(page)
        page.screenshot(path=OUT / "03-coding-passed-1366x768.png", full_page=True)

        with page.expect_response(lambda response: response.url.endswith("/submit") and response.request.method == "POST", timeout=30000) as submit_info:
            page.get_by_role("button", name="提交并生成诊断").click()
        assert submit_info.value.ok, f"正式提交失败: {submit_info.value.status} {submit_info.value.text()}"
        submit_payload = submit_info.value.json()["data"]
        assert submit_payload["execution"]["status"] == "PASSED", submit_payload

        after_submit = latest(api, token)
        assert len(after_submit.get("evidence") or []) > before_evidence, "正式提交必须新增学习证据"
        assert int((after_submit.get("snapshot") or {}).get("version") or 0) > before_version, "正式提交必须刷新诊断快照"

        page.get_by_role("button", name=re.compile("返回学习诊断")).click()
        page.get_by_role("heading", name="当前结论").wait_for(timeout=30000)
        assert not bad_responses, f"HTTP error responses: {bad_responses}"
        assert not console_errors, f"console errors: {console_errors}"
        assert not page_errors, f"page errors: {page_errors}"
        assert not failed, f"request failures: {failed}"
        print({
            "run_status": run_payload["status"],
            "failed_run_status": failed_run_payload["status"],
            "preview_evidence_delta": len(after_run.get("evidence") or []) - before_evidence,
            "submit_evidence_delta": len(after_submit.get("evidence") or []) - before_evidence,
            "snapshot_delta": int(after_submit["snapshot"]["version"]) - before_version,
            "console_errors": console_errors,
            "page_errors": page_errors,
            "failed": failed,
            "bad_responses": bad_responses,
            "output": str(OUT),
        })
        browser.close()
        api.dispose()


if __name__ == "__main__":
    main()
