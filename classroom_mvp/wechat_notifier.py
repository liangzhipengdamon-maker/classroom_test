"""
企业微信通知模块 - 消息推送

功能职责：
- send_to_wechat() - 发送拼图和评语到企业微信家长群
- 错误处理和日志记录
"""

import requests
import logging
from .config import WECHAT_WEBHOOK

logger = logging.getLogger(__name__)


def send_to_wechat(image_path, class_name, student_name, comment, image_url):
    """发送课堂记录拼图到企业微信家长群

    Args:
        image_path: 本地拼图文件路径（备用）
        class_name: 班级名称
        student_name: 学生名字
        comment: 评语文本
        image_url: 拼图的网络URL

    Returns:
        (success: bool, message: str)
    """
    try:
        # 企业微信消息格式（图文卡片）
        msg_data = {
            "msgtype": "news",
            "news": {
                "articles": [
                    {
                        "title": f"【课堂记录】{student_name} ({class_name})",
                        "description": comment,
                        "url": image_url,
                        "picurl": image_url,
                    }
                ]
            },
        }

        logger.info(f"📤 正在发送到企业微信: {student_name} ({class_name})")

        response = requests.post(WECHAT_WEBHOOK, json=msg_data, timeout=10)
        result = response.json()

        if result.get("errcode") == 0:
            logger.info("✅ 企业微信推送成功")
            return True, "已发送到家长群"
        else:
            error_msg = result.get("errmsg", "未知错误")
            logger.error(f"❌ 企业微信推送失败: {error_msg}")
            return False, error_msg

    except requests.exceptions.Timeout:
        error_msg = "请求超时"
        logger.error(f"❌ 企业微信推送超时: {error_msg}")
        return False, error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"网络错误: {str(e)}"
        logger.error(f"❌ 企业微信推送错误: {error_msg}")
        return False, error_msg

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ 企业微信推送异常: {error_msg}")
        return False, error_msg
