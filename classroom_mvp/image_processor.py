"""
图片处理模块 - 拼图生成

功能职责：
- create_collage() - 生成书法专用拼图（姿势+作品+评语+水印）
- 处理多种图片格式和大小
"""

import logging
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from .config import SCHOOL_NAME, COLLAGE_TARGET_WIDTH, COLLAGE_BOTTOM_HEIGHT

logger = logging.getLogger(__name__)


def create_collage(posture_path, work_path, output_path, class_name, student_name, comment):
    """生成书法专用拼图

    拼图包含：
    - 上半部分: 学生书写姿势照片
    - 中间部分: 书法作品照片
    - 下半部分: 课次信息、学生名字、评语、机构水印

    Args:
        posture_path: 书写姿势照片路径
        work_path: 书法作品照片路径
        output_path: 输出拼图路径
        class_name: 班级名称
        student_name: 学生名字
        comment: 评语文本

    Returns:
        bool: 生成是否成功
    """
    try:
        logger.info(f"🎨 开始生成拼图: {student_name} ({class_name})")

        # 加载并调整图片尺寸
        posture_img = Image.open(posture_path).convert("RGB")
        work_img = Image.open(work_path).convert("RGB")

        # 统一宽度（手机竖屏友好）
        target_width = COLLAGE_TARGET_WIDTH
        posture_ratio = target_width / posture_img.width
        work_ratio = target_width / work_img.width

        posture_img = posture_img.resize(
            (target_width, int(posture_img.height * posture_ratio)), Image.LANCZOS
        )
        work_img = work_img.resize(
            (target_width, int(work_img.height * work_ratio)), Image.LANCZOS
        )

        # 创建拼图画布（高度=姿势高+作品高+底部文字区）
        total_height = posture_img.height + work_img.height + COLLAGE_BOTTOM_HEIGHT
        collage = Image.new("RGB", (target_width, total_height), "#ffffff")

        # 粘贴图片
        collage.paste(posture_img, (0, 0))
        collage.paste(work_img, (0, posture_img.height))

        # 添加文字（使用系统字体，避免中文乱码）
        draw = ImageDraw.Draw(collage)
        font_large = _load_font(36)
        font_small = _load_font(28)

        text_y_base = posture_img.height + work_img.height

        # 课次信息
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        course_info = f"{now} | {class_name}"
        draw.text(
            (30, text_y_base + 20),
            course_info,
            fill="#2c3e50",
            font=font_small,
        )

        # 学生评语
        draw.text(
            (30, text_y_base + 60),
            f"📝 {student_name}：{comment}",
            fill="#27ae60",
            font=font_large,
        )

        # 机构水印
        watermark = f"雅趣堂｜{SCHOOL_NAME}"
        draw.text(
            (30, text_y_base + 120),
            watermark,
            fill="#95a5a6",
            font=font_small,
        )

        # 保存
        collage.save(output_path, quality=95, optimize=True)
        logger.info(f"✅ 拼图生成成功: {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ 拼图生成失败: {str(e)}")
        return False


def _load_font(size):
    """加载系统字体（支持中文）

    Args:
        size: 字体大小

    Returns:
        PIL Font 对象
    """
    try:
        # Windows 中文字体
        return ImageFont.truetype("simhei.ttf", size)
    except:
        try:
            # macOS 中文字体
            return ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", size)
        except:
            # 默认字体
            logger.warning("⚠️ 未找到中文字体，使用默认字体（可能显示乱码）")
            return ImageFont.load_default()
