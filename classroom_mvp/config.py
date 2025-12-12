"""
配置模块 - 环境变量加载和常量定义

功能职责：
- 加载 .env 环境变量
- 定义应用常量
- 配置 AI API 密钥和数据库路径
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ====== API 和认证配置 ======
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# ====== 企业微信配置 ======
WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=51a874dd-0727-4ce9-895e-8b090a4c3536"

# ====== 应用配置 ======
SCHOOL_NAME = "雅趣堂书画"
DOMAIN = "https://class.cangfengge.com"
UPLOAD_FOLDER = 'uploads'

# ====== 数据库配置 ======
RECORDS_FILE = "records.json"

# ====== AI 调用参数 ======
AI_MAX_RETRIES = 2
AI_RETRY_DELAY = 1
AI_MODEL = "qwen-vl-max"

# ====== 图片处理配置 ======
COLLAGE_TARGET_WIDTH = 750
COLLAGE_BOTTOM_HEIGHT = 250

# 创建上传目录
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
