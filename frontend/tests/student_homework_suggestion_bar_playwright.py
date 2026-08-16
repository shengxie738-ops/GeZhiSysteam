import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_rgb(value):
    match = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", value)
    if not match:
        raise AssertionError(f"Unexpected color format: {value}")
    red, green, blue = (int(match.group(i)) for i in range(1, 4))
    alpha = float(match.group(4) or 1)
    return red, green, blue, alpha


url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8088/index.html"
artifact_dir = Path("test-artifacts")
artifact_dir.mkdir(exist_ok=True)
screenshot_path = artifact_dir / "student-homework-alina-suggestion.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 2048, "height": 1152}, device_scale_factor=1)
    page.add_init_script(
        """
        localStorage.setItem('isLoggedIn', 'true');
        localStorage.setItem('currentRole', 'student');
        localStorage.setItem('currentView', 'homework');
        localStorage.setItem('homeworkMockFirst', 'true');
        localStorage.setItem('currentUser', JSON.stringify({
          username: 'student-demo',
          real_name: '',
          student_id: '',
          class_name: '',
          avatar_url: ''
        }));
        """
    )
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    bar = page.locator('[data-testid="student-homework-alina-suggestion"]')
    bar.wait_for(state="visible", timeout=15000)
    style = bar.evaluate(
        """
        (el) => {
          const computed = getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          return {
            backgroundColor: computed.backgroundColor,
            borderTopColor: computed.borderTopColor,
            width: rect.width,
            height: rect.height,
          };
        }
        """
    )
    red, green, blue, alpha = parse_rgb(style["backgroundColor"])
    assert min(red, green, blue) >= 245, style
    assert alpha >= 0.9, style
    assert style["width"] > 0 and style["height"] > 0, style
    page.screenshot(path=str(screenshot_path), full_page=True)
    browser.close()

print(f"student homework suggestion bar rendered bright white: {style['backgroundColor']}")
print(f"screenshot: {screenshot_path}")
