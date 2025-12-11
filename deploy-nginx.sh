#!/bin/bash
set -e  # 遇错立即退出

echo "🔧 正在部署 Nginx 配置 for classroom_mvp..."

# 配置变量
CONF_DIR="/etc/nginx/conf.d"
BACKUP_DIR="/root/nginx-backup-$(date +%Y%m%d-%H%M%S)"
NEW_CONF="$CONF_DIR/classroom-mvp.conf"

# 1. 创建备份目录
mkdir -p "$BACKUP_DIR"
echo "📦 备份现有配置到: $BACKUP_DIR"
cp "$CONF_DIR"/*.conf "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ 无现有 .conf 文件可备份"

# 2. 清理旧配置（保留 .bak 文件）
echo "🧹 清理旧配置文件（保留 .bak）..."
find "$CONF_DIR" -maxdepth 1 -name "*.conf" ! -name "*.bak" -delete

# 3. 写入新配置
cat > "$NEW_CONF" <<EOF
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
        alias /root/classroom_test/uploads/;
        expires 30d;
        add_header Cache-Control "public";
    }
}
EOF

echo "✅ 新配置已写入: $NEW_CONF"

# 4. 测试 Nginx 配置
echo "🧪 测试 Nginx 配置语法..."
if nginx -t; then
    echo "🔁 重载 Nginx 服务..."
    systemctl reload nginx
    echo "🎉 Nginx 配置部署成功！"
else
    echo "❌ Nginx 配置测试失败！恢复备份..."
    cp "$BACKUP_DIR"/*.conf "$CONF_DIR/" 2>/dev/null || true
    systemctl reload nginx
    exit 1
fi

# 5. 提示验证命令
echo
echo "🔍 建议验证命令："
echo "   curl -v http://localhost/upload"
echo "   journalctl -u classroom-mvp -f"