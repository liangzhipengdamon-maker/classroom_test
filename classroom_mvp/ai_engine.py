"""
AI 评语生成引擎模块

功能职责：
- generate_ai_comment(image_path, student_name, style) - 调用 Qwen-VL 生成评语
- 支持多风格评语生成（预留）
- 完整的容错和重试机制
- 详细的日志记录
"""

import time
import logging
from dashscope import MultiModalConversation
from .config import DASHSCOPE_API_KEY, AI_MAX_RETRIES, AI_RETRY_DELAY, AI_MODEL

logger = logging.getLogger(__name__)


def generate_ai_comment(image_path, student_name="学生", style="warm"):
    """调用 Qwen-VL 多模态大模型生成书法评语

    Args:
        image_path: 书法作品照片路径
        student_name: 学生名字（用于日志记录）
        style: 评语风格，预留参数（当前仅支持 "warm"）

    Returns:
        (comment, error, elapsed_ms): 
            - 成功: (评语文本, None, 耗时ms)
            - 失败: (None, 错误信息, 0)
    """
    if not DASHSCOPE_API_KEY:
        error_msg = "API Key 未配置"
        logger.error(f"❌ {error_msg}")
        return None, error_msg, 0

    # 根据风格选择提示词（第三周支持多风格）
    prompt_map = {
        "warm": "请根据这张书法作品，给出一段温暖、具体的评语，适合家长阅读。评语应该包括：(1)正面评价点，(2)可改进的地方，(3)鼓励语言。",
        "strict": "请根据这张书法作品，从技法角度给出专业的评语。重点分析笔画、笔顺、布局等方面的优缺点。",
        "encouraging": "请根据这张书法作品，给出一段激励式评语，强调进步和努力。",
    }
    prompt = prompt_map.get(style, prompt_map["warm"])

    for attempt in range(AI_MAX_RETRIES):
        try:
            # 日志记录
            if attempt == 0:
                logger.info(f"🔍 正在为 {student_name} 调用 Qwen-VL (风格: {style})...")
            else:
                logger.info(f"🔄 重试第 {attempt} 次调用 Qwen-VL...")

            start_time = time.time()

            # 构建消息体
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image_path},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            # 调用 Qwen-VL 多模态对话 API
            response = MultiModalConversation.call(
                model=AI_MODEL,
                messages=messages,
                api_key=DASHSCOPE_API_KEY,
            )

            # 检查响应
            if response.status_code == 200:
                # 提取生成的评语
                comment = response.output.choices[0].message.content
                # 如果是列表，取第一个文本内容
                if isinstance(comment, list):
                    for item in comment:
                        if isinstance(item, dict) and item.get("type") == "text":
                            comment = item.get("text", "")
                            break

                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"✅ AI 评语生成成功（耗时 {elapsed_ms}ms, 风格: {style}）"
                )
                return str(comment), None, elapsed_ms
            else:
                error_msg = (
                    response.message
                    if hasattr(response, "message")
                    else "未知错误"
                )
                logger.warning(
                    f"⚠️ AI 调用失败 (HTTP {response.status_code}): {error_msg}"
                )

                # 如果不是最后一次尝试，等待后重试
                if attempt < AI_MAX_RETRIES - 1:
                    time.sleep(AI_RETRY_DELAY)
                    continue
                else:
                    return None, f"AI 调用失败: {error_msg}", 0

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"⚠️ AI 调用异常 ({error_type}): {error_msg}")

            # 如果不是最后一次尝试，等待后重试
            if attempt < AI_MAX_RETRIES - 1:
                logger.info(f"   将在 {AI_RETRY_DELAY} 秒后重试...")
                time.sleep(AI_RETRY_DELAY)
                continue
            else:
                return None, "AI 评语生成暂时不可用，请稍后重试，或手动填写评语。", 0

    # 如果所有重试都失败
    return None, "AI 评语生成暂时不可用，请稍后重试，或手动填写评语。", 0
