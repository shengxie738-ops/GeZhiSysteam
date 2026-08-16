from pathlib import Path
import re

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "artifacts" / "learning-diagnosis-text-task-qa"
OUT.mkdir(parents=True, exist_ok=True)


def login_token(playwright):
    api = playwright.request.new_context(base_url="http://127.0.0.1:8516")
    response = api.post("/api/student/login", data={
        "username": "23001020119",
        "password": "123456",
        "role": "student",
    })
    assert response.ok, f"演示账号登录失败: {response.status} {response.text()}"
    return api, response.json()["data"]["token"]


def assert_no_page_overflow(page):
    size = page.evaluate("({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth})")
    assert size["scrollWidth"] <= size["clientWidth"] + 1, f"页面发生横向溢出: {size}"


def open_task(page, task_type):
    page.locator("button").filter(has_text=task_type).first.click()
    page.get_by_role("heading", name="学习材料").wait_for(timeout=30000)


def main():
    with sync_playwright() as p:
        api, token = login_token(p)
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
        page.get_by_role("heading", name="当前结论").wait_for(timeout=30000)

        open_task(page, "KNOWLEDGE_REVIEW")
        page.get_by_text("Agent guide", exact=True).wait_for()
        page.get_by_text("结构化复述", exact=True).click()
        answer = "链表边界条件需要先区分空链表、单节点、头节点和尾节点。处理前应判断当前结构，操作时更新 head、next 等引用，操作后再从头遍历并检查节点数量、头尾引用和连接关系，避免空指针或断链。以删除头节点为例，应先保存后继节点，再移动 head，并在链表变空时同步处理尾引用。最后通过空链表、单节点和多节点三组输入验证结构完整性。"
        editor = page.locator("textarea")
        editor.fill(answer)
        page.get_by_text("自由作答", exact=True).click()
        assert editor.input_value() == answer, "切换作答模式不应丢失内容"
        page.get_by_text(re.compile(r"概念覆盖 3 / 3")).wait_for()
        with page.expect_response(lambda response: "/hints?" in response.url and response.request.method == "POST", timeout=30000) as hint_info:
            page.get_by_role("button", name="获取下一层提示").click()
        assert hint_info.value.ok, f"知识回顾提示请求失败: {hint_info.value.status}"
        page.get_by_text(re.compile(r"Level 1 / 5")).wait_for()
        assert_no_page_overflow(page)
        page.screenshot(path=OUT / "01-review.png", full_page=True)
        with page.expect_response(lambda response: response.url.endswith("/submit") and response.request.method == "POST", timeout=30000) as submit_info:
            page.get_by_role("button", name="提交并生成诊断").click()
        assert submit_info.value.ok, f"知识回顾提交失败: {submit_info.value.status}"

        page.get_by_role("button", name=re.compile(r"返回学习诊断")).click()
        page.get_by_role("heading", name="当前结论").wait_for(timeout=30000)
        open_task(page, "GUIDED_PRACTICE")
        page.get_by_text("Guided practice", exact=False).first.wait_for()
        guided_answer = "我先确认题目要求和已知条件，再按顺序分析普通情况与边界情况。每一步都记录判断依据，先处理空输入和单节点，再进入普通节点流程，避免把所有场景强行套入同一逻辑。完成推理后，我会使用反例、边界输入和结果回代检查结论，并从头遍历结构确认节点数量与连接关系，确保最终答案不仅正确，而且能够解释为什么成立。"
        page.locator("textarea").fill(guided_answer)
        page.get_by_text(re.compile(r"概念覆盖 3 / 3")).wait_for()
        assert_no_page_overflow(page)
        page.screenshot(path=OUT / "02-guided.png", full_page=True)

        page.set_viewport_size({"width": 1366, "height": 768})
        assert_no_page_overflow(page)
        page.screenshot(path=OUT / "03-guided-1366x768.png", full_page=True)

        assert not console_errors, f"console errors: {console_errors}"
        assert not page_errors, f"page errors: {page_errors}"
        assert not failed, f"request failures: {failed}"
        print({"console_errors": console_errors, "page_errors": page_errors, "failed": failed, "output": str(OUT)})
        browser.close()
        api.dispose()


if __name__ == "__main__":
    main()
