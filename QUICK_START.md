# 🚀 InkSight 快速开始

## ⚡ 5 分钟快速验证

### 步骤 1: 安装依赖
```bash
cd /Users/Zhuanz/Documents/classroom_test
pip install -r requirements.txt
```

**预期输出**: `Successfully installed ...`

### 步骤 2: 运行测试
```bash
python test_inksight.py
```

**预期输出**:
```
🚀 InkSight 测试套件
====================================
✅ 导入测试通过
✅ 设备检测通过
⚠️ 模型初始化 (首次需要下载模型，约 500MB)
...
```

### 步骤 3: 尝试处理真实图像（可选）

1. 将书法作品图像放入 `uploads/` 目录
2. 重新运行 `python test_inksight.py`
3. 查看详细的笔迹分析结果

## 📝 代码示例

### 最简单的用法
```python
from utils.inksight_wrapper import extract_digital_ink

result = extract_digital_ink('uploads/student_work.jpg')
print(f"笔画数: {result['stroke_count']}, 置信度: {result['confidence']:.2%}")
```

### 集成到 Flask
```python
from flask import Flask
from utils.inksight_integration import analyze_handwriting

app = Flask(__name__)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    image_path = request.form.get('image_path')
    student_name = request.form.get('student_name')
    
    report = analyze_handwriting(image_path, student_name)
    return jsonify(report)
```

## 🎯 测试场景

| 场景 | 命令 | 预期结果 |
|------|------|---------|
| 快速诊断 | `python test_inksight.py` | 测试 1-3 通过，无需真实图像 |
| 完整测试 | 放入图像后运行 `python test_inksight.py` | 所有测试通过 |
| 单图处理 | `python -c "from utils.inksight_wrapper import extract_digital_ink; print(extract_digital_ink('uploads/image.jpg'))"` | 返回结构化结果 |
| 批处理 | 见 INKSIGHT_INTEGRATION_GUIDE.md | 处理整个目录的图像 |

## 🔍 常见问题

**Q: 模型下载太慢？**
A: 首次下载模型约 500MB，需要 1-5 分钟（取决于网络）。之后会缓存到 `utils/.inksight_cache/`

**Q: 能在 CPU 上运行吗？**
A: 可以！自动检测最优设备（GPU > MPS > CPU）

**Q: 如何强制使用 CPU？**
A: `extract_digital_ink('image.jpg', device='cpu')`

**Q: 内存不足？**
A: GPU OOM 时自动切换到 CPU，或手动指定设备

## 📚 完整文档

详见: [INKSIGHT_INTEGRATION_GUIDE.md](./INKSIGHT_INTEGRATION_GUIDE.md)

## ✨ 下一步

1. ✅ 验证安装 (`python test_inksight.py`)
2. ✅ 测试单张图像
3. ✅ 集成到 `class_mvp.py` (可选)
4. ✅ 配合 Qwen-VL 生成个性化评语 (可选)
