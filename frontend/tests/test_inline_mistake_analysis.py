import os
import sys
from playwright.sync_api import sync_playwright, expect

base_url = os.environ.get("TEST_BASE_URL", "http://localhost:5173/app/index.html")

print(f"Testing base URL: {base_url}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    
    # 监听控制台日志以进行排错
    page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
    
    # 注入登录与状态数据
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
    
    # 打开页面并等待网络空闲
    page.goto(base_url)
    page.wait_for_load_state("networkidle")
    
    # 导航到竞技排位赛
    expect(page.get_by_text("竞技排位赛").first).to_be_visible(timeout=10000)
    page.get_by_text("参加排位赛").click()
    
    # 等待大厅加载，然后切换到“错题本”页签
    expect(page.get_by_text("王者之路，由此启程")).to_be_visible(timeout=10000)
    page.get_by_test_id("ranked-tab-mistakes").click()
    
    # 确认错题本标题和错题项“岛屿数量”可见
    expect(page.get_by_text("直面错题，方能登顶")).to_be_visible(timeout=10000)
    expect(page.get_by_text("岛屿数量")).to_be_visible()
    
    # 截取错题本初始状态
    os.makedirs("test-artifacts", exist_ok=True)
    page.screenshot(path="test-artifacts/01-mistakes-initial.png")
    print("Step 1: Mistakes tab loaded successfully.")
    
    # 找到“岛屿数量”错题卡片，并定位其中的“AI 分析错题”按钮
    # 岛屿数量是卡片列表中的第一项
    mistake_card = page.locator("article").filter(has_text="岛屿数量")
    ai_btn = mistake_card.get_by_role("button", name="AI 分析错题")
    expect(ai_btn).to_be_visible()
    
    # 校验右侧 AI 教练面板当前是关闭的
    coach_drawer = page.locator("section.fixed:has-text('排位 AI 教练')")
    expect(coach_drawer).not_to_be_visible()
    
    # 点击“AI 分析错题”按钮
    ai_btn.click()
    print("Clicked 'AI 分析错题' button.")
    
    # 确认点击后按钮文字变成“分析中...”或“收起 AI 分析”（由于加载可能很快，可能直接变为“收起 AI 分析”）
    expect(mistake_card.get_by_role("button", name="收起 AI 分析")).to_be_visible(timeout=5000)
    print("Button text changed to '收起 AI 分析'.")
    
    # 确认内嵌分析面板展现
    inline_panel = mistake_card.locator("div:has-text('排位 AI 教练 · 错题诊断')").first
    expect(inline_panel).to_be_visible(timeout=5000)
    print("Inline analysis panel is visible.")
    
    # 校验内嵌面板中的三个精细化诊断分区是否可见
    expect(inline_panel.get_by_text("诊断结论")).to_be_visible()
    expect(inline_panel.get_by_text("核心考点")).to_be_visible()
    expect(inline_panel.get_by_text("针对练习")).to_be_visible()
    print("Verified the three specific analysis sections (Diagnosis, Concept, Practice).")
    
    # 校验右侧 AI 教练侧边抽屉面板依然保持关闭（没有错误地跳出来）
    expect(coach_drawer).not_to_be_visible()
    print("Verified that the right-side floating coach drawer remains CLOSED.")
    
    # 截取展开分析后的错题卡片
    page.screenshot(path="test-artifacts/02-inline-analysis-open.png")
    
    # 再次点击“收起 AI 分析”按钮，验证折叠收起功能
    collapse_btn = mistake_card.get_by_role("button", name="收起 AI 分析")
    collapse_btn.click()
    print("Clicked collapse button.")
    
    # 确认内嵌面板消失，按钮文字重新变回“AI 分析错题”
    expect(inline_panel).not_to_be_visible(timeout=5000)
    expect(mistake_card.get_by_role("button", name="AI 分析错题")).to_be_visible(timeout=5000)
    print("Inline panel collapsed and button text reverted.")
    
    # 截取收起后的卡片状态
    page.screenshot(path="test-artifacts/03-inline-analysis-collapsed.png")
    
    browser.close()

print("All inline mistake analysis E2E test assertions passed successfully!")
