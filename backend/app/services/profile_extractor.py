import json
import re
from app.core.database import SessionLocal
from app.models.student_profile import StudentProfile
from app.services.agent_workflow import llm_flash

async def extract_and_update_profile(user_id: str, message: str, reply: str):
    """
    后台异步提取并更新学生的 6 维画像。
    """
    # 过滤掉一些简短的打招呼
    if len(message.strip()) < 4:
        return

    prompt = f"""
你是一个教育学与人工智能专家。请分析以下学生与AI导师的最新对话，提取并评估该学生的最新学情画像特征。

【学生输入】: {message}
【导师回答】: {reply}

请依据对话内容，评估以下六个维度的最新状态：
1. 知识基础 (knowledge)：整数 (0-100) 或 null。如果学生在对话中展现了对新知识的掌握或解决了问题，可适当上调；如果展现出明显的概念盲区或代码报错，可下调。
2. 认知风格 (cognitive)：字符 (40字以内) 或 null。例如：“偏好代码实践”、“喜欢费曼技巧解说”、“喜欢递进式拆解”。
3. 学习步调 (pace)：整数 (0-100) 或 null。代表学生的学习节奏与反馈理解效率。
4. 易错点偏好 (error_pattern)：字符 (200字以内) 或 null。提取本次提问暴露的具体技术难点（如：“单链表反转指针丢失”、“对二叉树递归回溯理解薄弱”）。
5. 学习目标 (goal)：字符 (100字以内) 或 null。提取学生当前的具体学习意图（如“理解Vue3响应式”、“实现二分查找”）。
6. 专业背景 (background)：字符 (50字以内) 或 null。提取学生专业（如“计算机科学”、“通信工程”等）。

请严格按照以下 JSON 格式返回，不要带有任何 markdown ``` 格式或额外的分析文字，必须能够被 json.loads 解析：
{{
  "knowledge": null,
  "cognitive": null,
  "pace": null,
  "error_pattern": null,
  "goal": null,
  "background": null
}}
"""
    db = SessionLocal()
    try:
        response = llm_flash.invoke(prompt)
        content = response.content.strip()
        
        # 使用正则表达式匹配最外层的大括号 JSON 块，以提高对 LLM 冗余输出的稳健性
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        data = json.loads(content)
        
        # 获取或创建画像
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        if not profile:
            profile = StudentProfile(
                user_id=user_id,
                knowledge=50,
                cognitive="渐进理解型",
                pace=50,
                error_pattern="易错点：数组越界，指针空悬",
                goal="掌握核心数据结构与算法",
                background="电子信息与计算机类"
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
            
        # 动态更新提取到的字段
        if data.get("knowledge") is not None:
            # 限制在 10 到 100 之间，防过激上下调
            new_val = int(data["knowledge"])
            profile.knowledge = max(10, min(100, new_val))
            
        if data.get("cognitive"):
            profile.cognitive = data["cognitive"]
            
        if data.get("pace") is not None:
            profile.pace = max(10, min(100, int(data["pace"])))
            
        if data.get("error_pattern"):
            # 结合原有易错点追加，防直接覆盖
            old_err = profile.error_pattern or ""
            new_err = data["error_pattern"]
            if new_err not in old_err:
                profile.error_pattern = f"{new_err} | {old_err}"[:500]
                
        if data.get("goal"):
            profile.goal = data["goal"]
            
        if data.get("background"):
            profile.background = data["background"]
            
        db.commit()
        print(f"[Profile Extractor] Successfully updated profile for user: {user_id}")
    except Exception as e:
        db.rollback()
        print(f"[Profile Extractor] Error processing chat log for {user_id}: {e}")
    finally:
        db.close()
