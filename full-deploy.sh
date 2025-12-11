#!/bin/bash
set -e

echo "🚀 开始全自动部署 classroom_mvp 应用（彻底清理 + 全新安装）..."

# ========== 配置 ==========
APP_NAME="classroom_mvp"          # Python 模块名（文件名）
SERVICE_NAME="classroom-mvp"      # systemd 服务名
PROJECT_DIR="/root/$APP_NAME"
OLD_PROJECT_DIR="/root/classroom_test"
MAIN_PY_FILE="$APP_NAME.py"
NGINX_CONF="/etc/nginx/conf.d/${SERVICE_NAME}.conf"
NGINX_MAIN="/etc/nginx/nginx.conf"

# ========== 1. 清理旧服务 ==========
echo "🧹 正在停止并删除旧服务..."
systemctl stop moji classroom-mvp 2>/dev/null || true
systemctl disable moji classroom-mvp 2>/dev/null || true
rm -f /etc/systemd/system/moji.service /etc/systemd/system/classroom-mvp.service
systemctl daemon-reload

# ========== 2. 清理旧 Nginx 配置 ==========
echo "🧹 清理旧 Nginx 配置..."
rm -f /etc/nginx/conf.d/moji.conf /etc/nginx/conf.d/classroom-mvp.conf

# ========== 3. 恢复 nginx.conf 到原始状态（如果可能）==========
if ls /etc/nginx/nginx.conf.bak* 1> /dev/null 2>&1; then
    cp /etc/nginx/nginx.conf.bak* "$NGINX_MAIN"
    echo "🔄 已恢复 nginx.conf 备份"
elif [ -f /etc/nginx/nginx.conf.default ]; then
    cp /etc/nginx/nginx.conf.default "$NGINX_MAIN"
    echo "🔄 已恢复默认 nginx.conf"
else
    echo "ℹ️ 未找到备份，使用当前 nginx.conf"
fi

# ========== 4. 创建新项目目录 ==========
echo "📁 创建新项目目录: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR/uploads"

# ========== 5. 确保主程序存在 ==========
if [ -f "$PROJECT_DIR/$MAIN_PY_FILE" ]; then
    echo "✅ 主程序已存在: $PROJECT_DIR/$MAIN_PY_FILE"
elif [ -f "$OLD_PROJECT_DIR/class_mvp.py" ]; then
    echo "🚚 从旧位置移动主程序..."
    mv "$OLD_PROJECT_DIR/class_mvp.py" "$PROJECT_DIR/$MAIN_PY_FILE"
else
    echo "❌ 错误: 未找到主程序！请确保 class_mvp.py 或 classroom_mvp.py 存在。"
    exit 1
fi

# ========== 6. 创建/更新虚拟环境 ==========
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi
echo "📥 安装依赖..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install flask gunicorn requests pillow

# ========== 7. 创建 systemd 服务 ==========
echo "🔧 创建 systemd 服务: $SERVICE_NAME"
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Classroom MVP Service
After=network.target

[Service]
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/gunicorn -w 4 -b 127.0.0.1:5000 ${APP_NAME}:app
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
echo "✅ 服务 $SERVICE_NAME 已启动"

# ========== 8. 创建 Nginx 反向代理配置 ==========
echo "🌐 部署 Nginx 配置..."
cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }

    location /uploads/ {
        alias $PROJECT_DIR/uploads/;
        expires 30d;
    }
}
EOF

# ========== 9. 修复 OpenCloudOS 默认 server 冲突 ==========
echo "🛠️ 检查并注释 nginx.conf 中的默认 server 块..."
if grep -q '^[[:space:]]*server[[:space:]]*{' "$NGINX_MAIN" && \
   ! grep -q '^[[:space:]]*#.*server[[:space:]]*{' "$NGINX_MAIN"; then

    awk '
    BEGIN { in_server = 0; brace_count = 0 }
    /^[[:space:]]*server[[:space:]]*\{/ && !in_server {
        print "# " $0; in_server = 1; brace_count = 1; next
    }
    in_server {
        print "# " $0
        for (i = 1; i <= length($0); i++) {
            c = substr($0, i, 1)
            if (c == "{") brace_count++
            else if (c == "}") brace_count--
        }
        if (brace_count == 0) in_server = 0
        next
    }
    { print }
    ' "$NGINX_MAIN" > "${NGINX_MAIN}.tmp"

    mv "${NGINX_MAIN}.tmp" "$NGINX_MAIN"
    echo "✅ 默认 server 块已注释"
else
    echo "✅ nginx.conf 无需修改"
fi

# ========== 10. 重载 Nginx ==========
echo "🔄 重载 Nginx..."
if nginx -t; then
    systemctl reload nginx
    echo "✅ Nginx 配置已生效"
else
    echo "❌ Nginx 配置测试失败！"
    exit 1
fi

# ========== 11. 完成提示 ==========
echo
echo "🎉 全自动部署成功！"
echo
echo "🔍 验证步骤："
echo "  1. 本地测试: curl -v http://localhost/upload"
echo "  2. 公网访问: http://129.204.181.116/upload"
echo "  3. 查看日志: journalctl -u $SERVICE_NAME -f"
echo "  4. 提交表单后检查企业微信通知和 $PROJECT_DIR/uploads/ 目录"
echo
echo "💡 如需重新部署，直接再次运行此脚本即可。"