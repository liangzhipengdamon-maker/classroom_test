#!/bin/bash
set -e

echo "🚀 开始部署 classroom_mvp 应用..."

# === 配置变量 ===
PROJECT_DIR="/root/classroom_test"
VENV_DIR="$PROJECT_DIR/venv"
APP_MODULE="class_mvp:app"
SERVICE_NAME="classroom-mvp"
NGINX_CONF_DIR="/etc/nginx/conf.d"
NGINX_MAIN_CONF="/etc/nginx/nginx.conf"

# === 1. 确保项目目录存在 ===
mkdir -p "$PROJECT_DIR/uploads"
chmod 755 "$PROJECT_DIR/uploads"

# === 2. 创建/更新 Python 虚拟环境 ===
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

echo "📥 安装依赖..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install flask gunicorn requests pillow

# === 3. 确保 class_mvp.py 存在 ===
if [ ! -f "$PROJECT_DIR/class_mvp.py" ]; then
    echo "❌ 错误: $PROJECT_DIR/class_mvp.py 不存在！请先上传应用代码。"
    exit 1
fi

# === 4. 创建 systemd 服务 ===
echo "🔧 配置 systemd 服务..."
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Classroom MVP Service
After=network.target

[Service]
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/gunicorn -w 4 -b 127.0.0.1:5000 $APP_MODULE
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
echo "✅ 服务 $SERVICE_NAME 已启动"

# === 5. 部署 Nginx 配置（conf.d）===
echo "🌐 部署 Nginx 反向代理配置..."
mkdir -p "$NGINX_CONF_DIR"

# 清理旧配置（保留 .bak）
find "$NGINX_CONF_DIR" -name "*.conf" ! -name "*.bak" -delete

cat > "$NGINX_CONF_DIR/${SERVICE_NAME}.conf" <<EOF
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

# === 6. 修复 Nginx 主配置（关键！针对 OpenCloudOS）===
echo "🛠️ 检查并修复 Nginx 主配置冲突..."

# 备份主配置
BACKUP_MAIN="${NGINX_MAIN_CONF}.bak.$(date +%Y%m%d-%H%M%S)"
cp "$NGINX_MAIN_CONF" "$BACKUP_MAIN"

# 注释默认 server 块（如果存在且未注释）
if grep -q '^[[:space:]]*server[[:space:]]*{' "$NGINX_MAIN_CONF" && \
   ! grep -q '^[[:space:]]*#.*server[[:space:]]*{' "$NGINX_MAIN_CONF"; then

    awk '
    BEGIN { in_server = 0; brace_count = 0 }
    /^[[:space:]]*server[[:space:]]*\{/ && !in_server {
        print "# " $0
        in_server = 1
        brace_count = 1
        next
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
    ' "$NGINX_MAIN_CONF" > "${NGINX_MAIN_CONF}.tmp"

    mv "${NGINX_MAIN_CONF}.tmp" "$NGINX_MAIN_CONF"
    echo "✅ 默认 server 块已注释（备份: $BACKUP_MAIN）"
else
    echo "✅ 主配置无需修改"
fi

# === 7. 重载 Nginx ===
echo "🔄 重载 Nginx..."
if nginx -t; then
    systemctl reload nginx
    echo "✅ Nginx 配置已生效"
else
    echo "❌ Nginx 配置测试失败！恢复备份..."
    cp "$BACKUP_MAIN" "$NGINX_MAIN_CONF"
    systemctl reload nginx
    exit 1
fi

# === 8. 完成提示 ===
echo
echo "🎉 部署完成！"
echo
echo "🔍 验证步骤："
echo "  1. 本地测试: curl -v http://localhost/upload"
echo "  2. 公网访问: http://129.204.181.116/upload"
echo "  3. 查看日志: journalctl -u $SERVICE_NAME -f"
echo "  4. 提交表单后检查企业微信通知和 /uploads/ 目录"
echo
echo "💡 如需重新部署，直接再次运行此脚本即可。"