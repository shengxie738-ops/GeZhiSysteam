from pathlib import Path
import json
from playwright.sync_api import sync_playwright, expect


BASE_URL = "http://127.0.0.1:8088/index.html"
ORIGIN = "http://127.0.0.1:8088"
SCREENSHOT_DIR = Path("test-artifacts")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def python_repository_fixture(count=20):
    return [
        {
            "id": f"python-lab-{index:02d}",
            "title": f"Python 课程项目 {index:02d}",
            "slug": f"python-lab-{index:02d}",
            "description": "面向编译原理与数据库课程的 Python 实验仓库，包含 README、测试脚本和课程报告。",
            "author": "谢生",
            "avatar": "",
            "language": "Python",
            "course": ["编译原理", "计算机网络", "软件工程综合实训", "数据库系统原理"][index % 4],
            "tags": ["Python", "课程项目", "实验报告"],
            "collaborators": [],
            "visibility": "public",
            "status": "active",
            "recommendScore": 100 - index,
            "giteaOwner": "campus",
            "giteaRepo": f"python-lab-{index:02d}",
            "htmlUrl": f"https://gezhisystem.com/gitea/campus/python-lab-{index:02d}",
            "cloneUrl": f"https://gezhisystem.com/gitea/campus/python-lab-{index:02d}.git",
            "sshUrl": f"ssh://git@gezhisystem.com:2222/campus/python-lab-{index:02d}.git",
            "defaultBranch": "main",
            "archiveUrl": f"https://gezhisystem.com/gitea/campus/python-lab-{index:02d}/archive/main.zip",
            "readme": "# Python 课程项目\n\n用于课程实验与代码审阅。",
            "createdAt": f"2026-06-{index:02d}T08:00:00+08:00",
            "updatedAt": f"2026-07-{index:02d}T09:00:00+08:00",
            "starCount": index % 7,
            "favoriteCount": index % 5,
            "isStarred": False,
            "isFavorited": False,
        }
        for index in range(1, count + 1)
    ]


def new_page_with_state(browser, role, view, console_errors, repositories=None):
    user = {
        "username": "teacher-a" if role == "teacher" else "谢生",
        "real_name": "陈老师" if role == "teacher" else "谢生",
        "avatar_url": "",
    }
    context = browser.new_context(
        viewport={"width": 1440, "height": 920},
        storage_state={
            "cookies": [],
            "origins": [
                {
                    "origin": ORIGIN,
                    "localStorage": [
                        {"name": "isLoggedIn", "value": "true"},
                        {"name": "currentRole", "value": role},
                        {"name": "currentView", "value": view},
                        {"name": "isTeacherLogin", "value": "true" if role == "teacher" else "false"},
                        {"name": "currentUser", "value": json.dumps(user, ensure_ascii=False)},
                        {"name": "repositoryMockFirst", "value": "false" if repositories else "true"},
                    ],
                }
            ],
        },
    )
    page = context.new_page()
    if repositories is not None:
        page.route(
            "**/code-repositories?**",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json; charset=utf-8",
                body=json.dumps({"code": 200, "message": "ok", "data": repositories}, ensure_ascii=False),
            ),
        )
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.goto(BASE_URL, wait_until="networkidle")
    return context, page


def main():
    console_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        student_context, page = new_page_with_state(browser, "student", "academic-space", console_errors)
        expect(page.get_by_text("学术空间").first).to_be_visible(timeout=10000)
        expect(page.get_by_text("个人主页").first).to_be_visible()
        expect(page.get_by_text("代码仓库").first).to_be_visible()
        expect(page.get_by_text("代码拉取请求").first).to_be_visible()
        expect(page.get_by_text("收藏夹").first).to_be_visible()
        page.screenshot(path=str(SCREENSHOT_DIR / "student-academic-space.png"), full_page=True)

        page.get_by_text("代码仓库", exact=True).first.click()
        expect(page.get_by_text("热门项目仓库").first).to_be_visible(timeout=10000)
        expect(page.get_by_text("收藏最多").first).to_be_visible()
        expect(page.get_by_text("最相关").first).to_be_visible()
        student_context.close()

        dense_context, page = new_page_with_state(
            browser,
            "student",
            "academic-space",
            console_errors,
            repositories=python_repository_fixture(),
        )
        page.get_by_text("代码仓库", exact=True).first.click()
        expect(page.get_by_text("Python 课程项目 01").first).to_be_visible(timeout=10000)
        page.screenshot(path=str(SCREENSHOT_DIR / "student-code-repository-dense.png"), full_page=False)
        clipped_cards = page.evaluate(
            """() => Array.from(document.querySelectorAll('main article')).map((card) => {
                const rect = card.getBoundingClientRect();
                return {
                    text: card.innerText.slice(0, 80),
                    height: rect.height,
                    clientHeight: card.clientHeight,
                    scrollHeight: card.scrollHeight
                };
            }).filter((card) => card.scrollHeight > card.clientHeight + 1 || card.height < 132)"""
        )
        assert not clipped_cards, f"Repository cards should not shrink or clip content: {clipped_cards[:3]}"
        dense_context.close()

        teacher_context, page = new_page_with_state(browser, "teacher", "t_space", console_errors)
        expect(page.get_by_text("空间管理").first).to_be_visible(timeout=10000)
        expect(page.get_by_text("论坛管理").first).to_be_visible()
        expect(page.get_by_text("仓库审核").first).to_be_visible()
        expect(page.get_by_text("学术空间治理总览").first).to_be_visible()
        page.screenshot(path=str(SCREENSHOT_DIR / "teacher-space-manager.png"), full_page=True)
        teacher_context.close()

        browser.close()

    if console_errors:
        raise AssertionError("Console errors:\n" + "\n".join(console_errors))

    print("academic space browser checks passed")


if __name__ == "__main__":
    main()
