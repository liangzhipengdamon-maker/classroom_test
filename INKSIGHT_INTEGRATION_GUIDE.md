# InkSight 集成指南

## 📋 概述

本项目集成了 Google InkSight 模型进行**数字笔迹识别**和**笔画分析**。InkSight 是一个深度学习模型，用于：

- 🎨 **笔画识别**: 估计书法作品的笔画数量
- 📊 **笔迹特征提取**: 获取数字笔迹的特征向量
- 🎯 **教学分析**: 基于笔迹特征生成教学建议

## 🏗️ 项目结构

```
classroom_test/
├── utils/
│   ├── __init__.py
│   ├── inksight_official/          # Google 官方仓库（参考）
│   │   ├── README.md
│   │   ├── colab.ipynb
│   │   └── ...
│   ├── inksight_wrapper.py         # ✨ 核心封装模块
│   └── inksight_integration.py     # 集成接口
├── test_inksight.py                # 测试脚本
├── class_mvp.py                    # 主应用
├── requirements.txt                # 依赖文件
└── INKSIGHT_INTEGRATION_GUIDE.md   # 本文件
```

## 📦 依赖安装

### 方法 1: 使用 requirements.txt（推荐）

```bash
pip install -r requirements.txt
```

新增依赖：
- `torch>=2.0.0` - PyTorch 深度学习框架
- `torchvision>=0.15.0` - 计算机视觉工具包
- `transformers>=4.30.0` - Hugging Face Transformers 库
- `numpy>=1.24.0` - 数值计算库

### 方法 2: 手动安装

```bash
# 基础依赖（已存在）
pip install Flask==2.3.2 requests==2.31.0 Pillow==10.0.1 python-dotenv==1.0.0

# InkSight 新增依赖
pip install torch torchvision transformers numpy

# 可选：DashScope AI 评语
pip install dashscope
```

### 方法 3: 针对不同平台的优化安装

**Mac (Apple Silicon)**:
```bash
pip install torch torchvision -i https://download.pytorch.org/whl/torch_stable.html
pip install transformers
```

**Linux/Windows (CUDA)**:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install transformers
```

## 🚀 快速开始

### 1. 测试 InkSight 功能

运行完整的测试套件：

```bash
cd /Users/Zhuanz/Documents/classroom_test
python test_inksight.py
```

**测试内容**:
- ✅ 模块导入检查
- ✅ 设备检测（CPU/GPU/MPS）
- ✅ 模型加载验证
- ✅ 实际图像处理（可选）
- ✅ 集成示例演示

### 2. 单个图像处理

```python
from utils.inksight_wrapper import extract_digital_ink

# 提取图像的数字笔迹
result = extract_digital_ink('uploads/student_work.jpg')

print(f"笔画数: {result['stroke_count']}")
print(f"置信度: {result['confidence']:.4f}")
print(f"处理时间: {result['processing_time_ms']}ms")
```

### 3. 集成分析报告

```python
from utils.inksight_integration import analyze_handwriting, generate_handwriting_insights

# 分析书法作品
report = analyze_handwriting('uploads/student_work.jpg', '张三')

# 生成教学建议
insights = generate_handwriting_insights(report, '张三')
print(insights)
```

## 🔌 集成到 Flask 应用

### 示例 1: 在 `/upload` 路由中集成

```python
from utils.inksight_integration import analyze_handwriting, prepare_inksight_input

@app.route('/upload', methods=['POST'])
def upload():
    # ... 现有上传逻辑 ...
    
    if 'image' in request.files:
        file = request.files['image']
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        # 验证并处理图像
        image_path = prepare_inksight_input(filename)
        if image_path:
            # 执行 InkSight 分析
            analysis = analyze_handwriting(image_path, request.form.get('student_name'))
            
            # 保存分析结果到数据库
            record = {
                "image_path": filename,
                "inksight_analysis": analysis,
                # ... 其他字段 ...
            }
    
    return jsonify({"status": "success"})
```

### 示例 2: 新建 `/analyze` 路由

```python
@app.route('/api/analyze', methods=['POST'])
def analyze_handwriting_api():
    """InkSight 笔迹分析 API"""
    data = request.get_json()
    image_path = data.get('image_path')
    student_name = data.get('student_name', '学生')
    
    from utils.inksight_integration import analyze_handwriting
    
    result = analyze_handwriting(image_path, student_name)
    
    return jsonify({
        "success": result["success"],
        "stroke_count": result["stroke_analysis"].get("estimated_stroke_count"),
        "confidence": result["stroke_analysis"].get("confidence"),
        "error": result["error"]
    })
```

## 📊 返回数据格式

### extract_digital_ink() 返回值

```python
{
    "success": True,
    "image_path": "uploads/work.jpg",
    "device": "cuda",
    "features": [0.123, 0.456, ...],          # 特征向量
    "stroke_count": 8,                         # 估计笔画数
    "confidence": 0.92,                        # 置信度 (0-1)
    "error": None,
    "processing_time_ms": 250.5
}
```

### analyze_handwriting() 返回值

```python
{
    "success": True,
    "student": "张三",
    "stroke_analysis": {
        "estimated_stroke_count": 8,
        "confidence": 0.92,
        "device_used": "cuda",
        "processing_time_ms": 250.5
    },
    "ink_features": {
        "feature_vector_size": 256,
        "feature_dimension": "embedding",
        "sample_features": [0.123, 0.456, ...]
    },
    "recommendations": [],
    "error": None
}
```

## 🧪 测试场景

### 场景 1: 快速功能验证

```bash
# 不需要真实图像，仅验证导入和初始化
python test_inksight.py

# 预期输出: 测试 1-3 通过，测试 4 可跳过
```

### 场景 2: 单张图像处理

```bash
# 1. 将测试图像放入 uploads/ 目录
cp ~/Desktop/sample.jpg uploads/

# 2. 运行完整测试
python test_inksight.py

# 3. 查看详细处理结果
```

### 场景 3: 批量处理

```python
from utils.inksight_wrapper import InkSightExtractor

extractor = InkSightExtractor()
results = extractor.batch_extract('uploads/')

for result in results:
    print(f"{result['image_path']}: 笔画数 {result['stroke_count']}")
```

## ⚙️ 高级配置

### 自定义设备选择

```python
from utils.inksight_wrapper import extract_digital_ink

# 强制使用 CPU
result = extract_digital_ink('uploads/work.jpg', device='cpu')

# 强制使用 GPU
result = extract_digital_ink('uploads/work.jpg', device='cuda')

# Mac Apple Silicon
result = extract_digital_ink('uploads/work.jpg', device='mps')
```

### 模型缓存管理

```python
from utils.inksight_wrapper import InkSightExtractor

# 启用缓存（默认）- 模型保存在 utils/.inksight_cache/
extractor = InkSightExtractor(use_cache=True)

# 禁用缓存 - 每次加载都重新下载
extractor = InkSightExtractor(use_cache=False)

# 清理缓存
import shutil
shutil.rmtree('utils/.inksight_cache')
```

### 日志配置

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 或针对特定模块
logging.getLogger('utils.inksight_wrapper').setLevel(logging.DEBUG)
```

## 🐛 故障排查

### 问题 1: `ModuleNotFoundError: No module named 'transformers'`

**解决方案**:
```bash
pip install transformers>=4.30.0
```

### 问题 2: `torch.cuda.OutOfMemoryError`

**原因**: GPU 内存不足

**解决方案**:
```python
# 自动切换到 CPU
result = extract_digital_ink('uploads/work.jpg')  # 会自动降级

# 或手动指定 CPU
result = extract_digital_ink('uploads/work.jpg', device='cpu')
```

### 问题 3: 模型下载缓慢或失败

**原因**: Hugging Face 网络连接问题

**解决方案**:
```bash
# 1. 设置国内镜像（可选）
export HF_ENDPOINT=https://huggingface.co

# 2. 手动下载模型
huggingface-cli download Derendering/InkSight-Small-p

# 3. 或使用本地模型路径
```

### 问题 4: 图像处理失败 - "Image is not valid"

**原因**: 图像格式不支持或损坏

**解决方案**:
```bash
# 确保图像格式为 JPEG/PNG
file uploads/image.jpg

# 转换格式（如果需要）
python -c "from PIL import Image; Image.open('bad.jpg').convert('RGB').save('good.jpg')"
```

## 📈 性能优化

### 1. 批量处理优化

```python
# ❌ 不推荐：逐一处理（每次都加载模型）
for image in images:
    result = extract_digital_ink(image)

# ✅ 推荐：使用单例模式
from utils.inksight_wrapper import get_extractor
extractor = get_extractor()
for image in images:
    result = extractor.extract_digital_ink(image)
```

### 2. 内存管理

```python
from utils.inksight_wrapper import get_extractor

extractor = get_extractor()

# 处理完毕后清理
extractor.cleanup()

# 下次需要时会自动重新加载
```

### 3. 异步处理（可选）

```python
from concurrent.futures import ThreadPoolExecutor
from utils.inksight_wrapper import extract_digital_ink

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(extract_digital_ink, img) for img in images]
    results = [f.result() for f in futures]
```

## 📚 参考资源

- **Google InkSight 官方仓库**: https://github.com/google-research/inksight
- **Hugging Face Transformers**: https://huggingface.co/docs/transformers
- **PyTorch 文档**: https://pytorch.org/docs
- **模型卡片**: https://huggingface.co/Derendering/InkSight-Small-p

## 🎯 后续扩展方案

### 方案 1: 集成 Qwen-VL 生成个性化评语

```python
from utils.inksight_integration import analyze_handwriting
from generate_ai_comment import generate_ai_comment

# 先进行 InkSight 分析
analysis = analyze_handwriting(image_path, student_name)

# 基于分析结果和图像生成评语
if analysis['success']:
    comment, error, elapsed_ms = generate_ai_comment(
        image_path, 
        student_name,
        context=f"笔画数: {analysis['stroke_analysis']['estimated_stroke_count']}"
    )
```

### 方案 2: 构建进度追踪系统

```python
# 保存 InkSight 分析结果到 records.json
record = {
    "timestamp": datetime.now().isoformat(),
    "student": student_name,
    "inksight_analysis": analysis,
    "stroke_trend": [8, 9, 8, 7]  # 历次笔画数趋势
}
```

### 方案 3: 实现书法水平分级

```python
def classify_handwriting_level(analysis_report):
    """基于笔迹特征分级"""
    stroke_count = analysis_report['stroke_analysis']['estimated_stroke_count']
    confidence = analysis_report['stroke_analysis']['confidence']
    
    if confidence > 0.9 and stroke_count > 10:
        return "优秀 ⭐⭐⭐"
    elif confidence > 0.7 and stroke_count > 5:
        return "良好 ⭐⭐"
    else:
        return "需改进 ⭐"
```

## 📞 支持

遇到问题？

1. 查看上方 **故障排查** 章节
2. 运行 `python test_inksight.py` 诊断环境
3. 检查 `class_mvp.py` 中的日志输出
4. 参考官方仓库: https://github.com/google-research/inksight

---

✨ **InkSight 集成完成！** 现在你可以为书法学生提供 AI 驱动的个性化评语了。
