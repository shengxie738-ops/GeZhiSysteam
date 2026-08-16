"""pytest 全局环境准备。

conftest.py 在任何测试模块导入之前加载，确保依赖环境变量的模块
（如 app.services.model_registry 在导入时读取密钥）拿到占位值。
"""

import os

# 模型注册表密钥占位（真实密钥仅存在于部署环境的 .env）
os.environ.setdefault("ZHIPU_API_KEY", "test")
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "test"))
