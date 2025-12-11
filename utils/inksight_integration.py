"""
InkSight 与 Flask 应用的集成示例
展示如何将笔迹识别功能集成到现有的评语生成系统中
"""

from utils.inksight_wrapper import extract_digital_ink, InkSightExtractor
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def analyze_handwriting(image_path: str, student_name: str = "学生") -> Dict:
    """
    分析书法图像并生成笔迹分析报告
    
    Args:
        image_path: 书法图像路径
        student_name: 学生姓名（用于日志）
    
    Returns:
        分析报告字典，包含：
        - success: 是否成功
        - student: 学生姓名
        - stroke_analysis: 笔画分析
        - ink_features: 数字笔迹特征
        - recommendations: AI 建议（可选，集成 Qwen）
        - error: 错误信息
    """
    report = {
        "success": False,
        "student": student_name,
        "stroke_analysis": {},
        "ink_features": {},
        "recommendations": [],
        "error": None
    }
    
    try:
        # 使用 InkSight 提取笔迹
        logger.info(f"🎨 分析 {student_name} 的书法作品: {image_path}")
        result = extract_digital_ink(image_path)
        
        if not result["success"]:
            report["error"] = result["error"]
            logger.error(f"❌ 笔迹提取失败: {report['error']}")
            return report
        
        # 笔画分析
        report["stroke_analysis"] = {
            "estimated_stroke_count": result["stroke_count"],
            "confidence": result["confidence"],
            "device_used": result["device"],
            "processing_time_ms": result["processing_time_ms"]
        }
        
        # 数字笔迹特征
        features = result["features"]
        report["ink_features"] = {
            "feature_vector_size": len(features) if isinstance(features, list) else features.shape[0],
            "feature_dimension": "embedding" if len(features) > 100 else "classification",
            "sample_features": features[:10] if isinstance(features, list) else features[:10].tolist()
        }
        
        report["success"] = True
        logger.info(f"✅ {student_name} 的笔迹分析完成 | 笔画数: {result['stroke_count']}")
        
    except Exception as e:
        report["error"] = f"分析异常: {str(e)}"
        logger.error(report["error"])
    
    return report


def generate_handwriting_insights(analysis_report: Dict, student_name: str = "学生") -> str:
    """
    基于笔迹分析生成教学建议（可选集成 Qwen-VL）
    
    当前版本：结合笔画特征生成规则化建议
    未来版本：集成 Qwen-VL 生成个性化评语
    
    Args:
        analysis_report: analyze_handwriting() 返回的分析报告
        student_name: 学生姓名
    
    Returns:
        教学建议文本
    """
    if not analysis_report.get("success"):
        return f"⚠️ 无法生成 {student_name} 的书法建议，笔迹提取失败。"
    
    stroke_count = analysis_report["stroke_analysis"]["estimated_stroke_count"]
    confidence = analysis_report["stroke_analysis"]["confidence"]
    
    # 规则化建议生成逻辑
    insights = f"📝 {student_name} 的书法分析:\n"
    insights += f"- 估计笔画数: {stroke_count}\n"
    insights += f"- 识别置信度: {confidence:.2%}\n"
    
    if confidence < 0.5:
        insights += "- 💡 建议: 笔迹特征可能不清晰，请确保拍照光线充足\n"
    elif stroke_count < 5:
        insights += "- 💡 建议: 笔画相对简洁，注意笔画的连贯性和力度变化\n"
    else:
        insights += "- 💡 建议: 笔画丰富，继续保持笔画之间的平衡与统一\n"
    
    insights += f"- 🎯 后续: 使用 Qwen-VL 生成更个性化的评语"
    
    return insights


def prepare_inksight_input(uploaded_file_path: str, upload_dir: str = "uploads") -> Optional[str]:
    """
    准备 InkSight 输入：验证并归一化图像
    
    Args:
        uploaded_file_path: 上传的文件路径（相对于上传目录）
        upload_dir: 上传目录名称
    
    Returns:
        规范化的图像路径，或 None（验证失败）
    """
    import os
    from PIL import Image
    
    full_path = os.path.join(upload_dir, uploaded_file_path)
    
    if not os.path.exists(full_path):
        logger.error(f"❌ 文件不存在: {full_path}")
        return None
    
    try:
        # 验证是否为有效的图像
        img = Image.open(full_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
            # 可选：保存转换后的图像
            img.save(full_path, quality=95)
        
        logger.info(f"✅ 图像验证通过: {full_path} (Size: {img.size})")
        return full_path
    
    except Exception as e:
        logger.error(f"❌ 图像验证失败: {str(e)}")
        return None


# 测试接口（用于 Flask 路由）
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("✅ InkSight 集成模块已就绪")
    print("\n集成到 class_mvp.py 的使用流程:")
    print("1. 在 submit_record() 中调用: prepare_inksight_input()")
    print("2. 验证通过后调用: analyze_handwriting()")
    print("3. 可选：调用 generate_handwriting_insights() 或集成 Qwen-VL")
