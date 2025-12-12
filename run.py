#!/usr/bin/env python3
"""
雅趣智能课堂反馈系统启动脚本

用法:
    python run.py

这是模块化重构后的新启动方式（替代原 class_mvp.py）
"""

from classroom_mvp.app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
