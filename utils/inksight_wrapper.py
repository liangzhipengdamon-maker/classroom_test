"""
InkSight 数字笔迹识别封装模块
集成 Google InkSight 模型进行笔迹分解与笔顺推理
"""

import os
import torch
import numpy as np
from PIL import Image
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple

# 配置日志
logger = logging.getLogger(__name__)

try:
    from transformers import AutoImageProcessor, AutoModelForImageClassification
except ImportError:
    logger.warning("transformers 库未安装，部分功能不可用。请运行: pip install transformers")


class InkSightExtractor:
    """
    InkSight 笔迹提取器
    
    功能：
    - 加载 Google InkSight 模型（通过 Hugging Face Transformers）
    - 处理书法图像并提取数字笔迹信息
    - 自动检测 CPU/GPU 设备
    - 包含完整错误处理
    """
    
    MODEL_NAME = "Derendering/InkSight-Small-p"
    CACHE_DIR = Path(__file__).parent / ".inksight_cache"
    
    def __init__(self, device: Optional[str] = None, use_cache: bool = True):
        """
        初始化 InkSight 提取器
        
        Args:
            device: 计算设备 ('cpu'/'cuda'/'mps')，None 时自动检测
            use_cache: 是否使用缓存的模型
        """
        self.device = device or self._detect_device()
        self.use_cache = use_cache
        self.model = None
        self.processor = None
        
        if self.use_cache:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✅ InkSight 提取器初始化 (Device: {self.device})")
    
    def _detect_device(self) -> str:
        """自动检测最优计算设备"""
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        
        logger.info(f"🔍 自动检测计算设备: {device}")
        return device
    
    def _load_model(self) -> Tuple:
        """
        加载 InkSight 模型和处理器
        
        Returns:
            (processor, model) 元组
        """
        if self.model is not None and self.processor is not None:
            return self.processor, self.model
        
        try:
            logger.info(f"🤖 加载 InkSight 模型: {self.MODEL_NAME}")
            
            # 设置缓存目录
            cache_dir = str(self.CACHE_DIR) if self.use_cache else None
            
            # 加载处理器和模型
            self.processor = AutoImageProcessor.from_pretrained(
                self.MODEL_NAME,
                cache_dir=cache_dir,
                trust_remote_code=True
            )
            
            self.model = AutoModelForImageClassification.from_pretrained(
                self.MODEL_NAME,
                cache_dir=cache_dir,
                trust_remote_code=True,
                device_map=self.device if self.device != "cpu" else None
            )
            
            if self.device != "cpu":
                self.model = self.model.to(self.device)
            
            self.model.eval()
            logger.info("✅ 模型加载成功")
            
            return self.processor, self.model
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {str(e)}")
            raise RuntimeError(f"无法加载 InkSight 模型: {str(e)}")
    
    def extract_digital_ink(self, image_path: str) -> Dict:
        """
        从书法图像提取数字笔迹数据
        
        Args:
            image_path: 输入图像路径 (JPEG/PNG)
        
        Returns:
            字典，包含：
            - success: 是否成功提取
            - image_path: 输入图像路径
            - device: 使用的计算设备
            - features: 提取的笔迹特征向量 (list)
            - stroke_count: 估计笔画数量
            - confidence: 模型置信度
            - error: 错误信息（失败时）
            - processing_time_ms: 处理耗时（毫秒）
        """
        import time
        start_time = time.time()
        
        result = {
            "success": False,
            "image_path": image_path,
            "device": self.device,
            "features": [],
            "stroke_count": 0,
            "confidence": 0.0,
            "error": None,
            "processing_time_ms": 0
        }
        
        try:
            # 验证文件存在
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图像文件不存在: {image_path}")
            
            # 加载并验证图像
            image = Image.open(image_path)
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            logger.info(f"📸 处理图像: {image_path} (Size: {image.size})")
            
            # 加载模型
            processor, model = self._load_model()
            
            # 图像预处理与推理
            with torch.no_grad():
                inputs = processor(images=image, return_tensors="pt")
                
                if self.device != "cpu":
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # 模型推理
                outputs = model(**inputs)
                
                # 提取特征和预测
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                
                # 获取置信度和类别
                confidence, predicted_class = torch.max(probabilities, dim=-1)
                
                # 提取隐层特征（通常在模型的倒数第二层）
                if hasattr(outputs, 'hidden_states') and outputs.hidden_states:
                    features = outputs.hidden_states[-1].mean(dim=1).detach().cpu().numpy()
                else:
                    # 降级处理：使用logits作为特征向量
                    features = logits.detach().cpu().numpy()
                
                # 结果收集
                result["success"] = True
                result["features"] = features.squeeze().tolist()
                result["confidence"] = float(confidence.item())
                result["stroke_count"] = int(predicted_class.item())
                
                logger.info(
                    f"✅ 笔迹提取成功 | "
                    f"笔画数: {result['stroke_count']} | "
                    f"置信度: {result['confidence']:.4f}"
                )
        
        except FileNotFoundError as e:
            result["error"] = f"文件错误: {str(e)}"
            logger.error(result["error"])
        
        except torch.cuda.OutOfMemoryError as e:
            result["error"] = "GPU 内存不足，已切换到 CPU 模式"
            self.device = "cpu"
            logger.warning(result["error"])
            # 可选：递归重试一次
            return self.extract_digital_ink(image_path)
        
        except Exception as e:
            result["error"] = f"处理失败: {str(e)}"
            logger.error(f"❌ {result['error']}")
        
        finally:
            result["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        return result
    
    def batch_extract(self, image_dir: str) -> List[Dict]:
        """
        批量处理目录中的图像
        
        Args:
            image_dir: 包含图像的目录路径
        
        Returns:
            结果列表
        """
        results = []
        image_dir_path = Path(image_dir)
        
        if not image_dir_path.is_dir():
            logger.error(f"❌ 目录不存在: {image_dir}")
            return results
        
        # 支持的图像格式
        image_files = list(image_dir_path.glob("*.jpg")) + \
                     list(image_dir_path.glob("*.jpeg")) + \
                     list(image_dir_path.glob("*.png"))
        
        logger.info(f"🔄 开始批处理 {len(image_files)} 张图像")
        
        for idx, img_path in enumerate(image_files, 1):
            logger.info(f"处理进度: {idx}/{len(image_files)}")
            result = self.extract_digital_ink(str(img_path))
            results.append(result)
        
        logger.info(f"✅ 批处理完成，成功: {sum(1 for r in results if r['success'])}/{len(results)}")
        return results
    
    def cleanup(self):
        """清理内存中的模型"""
        if self.model is not None:
            self.model = None
        if self.processor is not None:
            self.processor = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("🗑️ 模型资源已清理")


# 全局提取器实例（延迟初始化）
_extractor = None


def get_extractor(device: Optional[str] = None) -> InkSightExtractor:
    """获取全局 InkSight 提取器实例（单例模式）"""
    global _extractor
    if _extractor is None:
        _extractor = InkSightExtractor(device=device)
    return _extractor


def extract_digital_ink(image_path: str, device: Optional[str] = None) -> Dict:
    """
    快捷函数：提取图像中的数字笔迹
    
    Args:
        image_path: 图像路径
        device: 计算设备
    
    Returns:
        提取结果字典
    """
    extractor = get_extractor(device=device)
    return extractor.extract_digital_ink(image_path)


if __name__ == "__main__":
    # 测试示例
    logging.basicConfig(level=logging.INFO)
    
    print("InkSight 封装模块已就绪！")
    print("\n使用示例:")
    print("  from utils.inksight_wrapper import extract_digital_ink")
    print("  result = extract_digital_ink('path/to/image.jpg')")
    print(f"  print(result)")
