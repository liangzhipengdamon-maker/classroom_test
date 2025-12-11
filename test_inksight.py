#!/usr/bin/env python3
"""
InkSight 功能测试脚本

测试场景：
1. 模型加载测试（无需真实图像）
2. 单张图像处理测试
3. 批量处理测试
4. 集成示例演示
"""

import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """测试导入"""
    logger.info("=" * 60)
    logger.info("测试 1: 检查导入")
    logger.info("=" * 60)
    
    try:
        from utils.inksight_wrapper import InkSightExtractor, get_extractor
        logger.info("✅ InkSightExtractor 导入成功")
        
        from utils.inksight_integration import (
            analyze_handwriting,
            generate_handwriting_insights,
            prepare_inksight_input
        )
        logger.info("✅ 集成模块导入成功")
        
        return True
    except ImportError as e:
        logger.error(f"❌ 导入失败: {e}")
        return False


def test_device_detection():
    """测试设备检测"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 设备检测")
    logger.info("=" * 60)
    
    try:
        import torch
        logger.info(f"PyTorch 版本: {torch.__version__}")
        
        if torch.cuda.is_available():
            logger.info(f"✅ CUDA 可用: {torch.cuda.get_device_name(0)}")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("✅ MPS (Apple Silicon) 可用")
        else:
            logger.info("⚠️ 将使用 CPU (性能较低)")
        
        return True
    except ImportError:
        logger.warning("⚠️ PyTorch 未安装，部分功能不可用")
        return False


def test_model_initialization():
    """测试模型初始化"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: 模型初始化")
    logger.info("=" * 60)
    
    try:
        from utils.inksight_wrapper import InkSightExtractor
        
        logger.info("初始化 InkSightExtractor...")
        extractor = InkSightExtractor(use_cache=True)
        logger.info(f"✅ 提取器初始化成功 (Device: {extractor.device})")
        
        # 可选：尝试加载模型（需要网络）
        logger.info("\n⏳ 尝试加载模型（首次加载需要下载，请耐心等待）...")
        try:
            processor, model = extractor._load_model()
            logger.info("✅ 模型加载成功")
            logger.info(f"   模型类型: {type(model).__name__}")
            logger.info(f"   处理器类型: {type(processor).__name__}")
        except Exception as e:
            logger.warning(f"⚠️ 模型加载失败（可能是网络问题）: {e}")
            logger.info("   提示: 需要网络连接才能从 Hugging Face 下载模型")
        
        # 清理资源
        extractor.cleanup()
        logger.info("✅ 资源清理成功")
        
        return True
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        return False


def test_with_sample_image():
    """使用示例图像测试"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 4: 图像处理测试")
    logger.info("=" * 60)
    
    # 检查是否有示例图像
    sample_dir = Path(__file__).parent / "uploads"
    if not sample_dir.exists():
        logger.info("ℹ️ uploads 目录不存在，跳过实际图像处理测试")
        logger.info("   提示: 将图像放在 uploads/ 目录下可进行实际测试")
        return None
    
    image_files = list(sample_dir.glob("*.jpg")) + list(sample_dir.glob("*.png"))
    
    if not image_files:
        logger.info("ℹ️ uploads 目录中没有找到图像文件")
        logger.info("   提示: 放置 JPG/PNG 图像后重新测试")
        return None
    
    try:
        from utils.inksight_wrapper import extract_digital_ink
        from utils.inksight_integration import analyze_handwriting
        
        test_image = str(image_files[0])
        logger.info(f"\n处理图像: {test_image}")
        
        # 直接提取
        logger.info("执行 extract_digital_ink()...")
        result = extract_digital_ink(test_image)
        
        logger.info(f"结果:")
        logger.info(f"  - 成功: {result['success']}")
        logger.info(f"  - 笔画数: {result['stroke_count']}")
        logger.info(f"  - 置信度: {result['confidence']:.4f}")
        logger.info(f"  - 处理时间: {result['processing_time_ms']}ms")
        if result['error']:
            logger.error(f"  - 错误: {result['error']}")
        
        # 集成分析
        logger.info("\n执行 analyze_handwriting()...")
        analysis = analyze_handwriting(test_image, "张三")
        logger.info(f"分析报告:")
        logger.info(f"  - 成功: {analysis['success']}")
        if analysis['success']:
            logger.info(f"  - 笔画数: {analysis['stroke_analysis']['estimated_stroke_count']}")
            logger.info(f"  - 特征向量大小: {analysis['ink_features']['feature_vector_size']}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_example():
    """测试集成示例"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 5: 集成示例演示")
    logger.info("=" * 60)
    
    try:
        from utils.inksight_integration import generate_handwriting_insights
        
        # 模拟分析报告
        mock_report = {
            "success": True,
            "student": "李四",
            "stroke_analysis": {
                "estimated_stroke_count": 8,
                "confidence": 0.92,
                "device_used": "cpu",
                "processing_time_ms": 250
            },
            "ink_features": {
                "feature_vector_size": 256,
                "feature_dimension": "embedding"
            }
        }
        
        insights = generate_handwriting_insights(mock_report, "李四")
        logger.info("生成的教学建议:")
        for line in insights.split('\n'):
            logger.info(f"  {line}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    logger.info("\n")
    logger.info("🚀 InkSight 测试套件")
    logger.info("=" * 60)
    
    results = {}
    
    # 运行测试
    results["导入"] = test_imports()
    results["设备检测"] = test_device_detection()
    results["模型初始化"] = test_model_initialization()
    results["图像处理"] = test_with_sample_image()
    results["集成示例"] = test_integration_example()
    
    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 测试汇总")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        if result is None:
            status = "⏭️  跳过"
        elif result:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        logger.info(f"{test_name:15} {status}")
    
    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)
    
    logger.info("=" * 60)
    if total > 0:
        logger.info(f"✨ 通过率: {passed}/{total}")
    
    logger.info("\n📚 后续步骤:")
    logger.info("1. 在 uploads/ 目录放置测试图像")
    logger.info("2. 运行此脚本: python test_inksight.py")
    logger.info("3. 在 class_mvp.py 中集成 InkSight（可选）")
    logger.info("\n💡 集成到 Flask 应用的示例:")
    logger.info("   from utils.inksight_integration import analyze_handwriting")
    logger.info("   result = analyze_handwriting('uploads/student_work.jpg')")


if __name__ == "__main__":
    main()
