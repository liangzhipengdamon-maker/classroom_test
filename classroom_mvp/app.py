"""
Flask 应用主入口 - 所有路由和 API 端点

功能职责：
- 初始化 Flask 应用
- 定义所有路由（/upload, /api/submit, /stats, /export, /archive 等）
- 处理表单提交和文件上传
- 生成 HTML 页面和 API 响应
"""

import os
import uuid
import logging
from datetime import datetime
from urllib.parse import quote, unquote

from flask import (
    Flask,
    request,
    render_template_string,
    send_from_directory,
    jsonify,
)

# 导入各个模块
from .config import (
    DASHSCOPE_API_KEY,
    SCHOOL_NAME,
    DOMAIN,
    UPLOAD_FOLDER,
)
from .ai_engine import generate_ai_comment
from .data_manager import load_records, filter_records, records_to_csv, save_record, get_all_classes
from .wechat_notifier import send_to_wechat
from .image_processor import create_collage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 初始化 Flask 应用
app = Flask(__name__)

# ====== 前端路由 ======

@app.route("/")
def home():
    """首页（重定向到上传页）"""
    return '<script>window.location.href="/upload"</script>'


@app.route("/upload")
def upload_page():
    """教师手机端上传页面"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>雅趣智能课堂反馈｜上传</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; font-family:"PingFang SC","Microsoft YaHei",sans-serif; }
            body { padding:20px; background:#f8f9fa; color:#333; }
            .container { max-width:600px; margin:0 auto; background:white; border-radius:16px; padding:25px; box-shadow:0 4px 12px rgba(0,0,0,0.05); }
            h2 { text-align:center; color:#e74c3c; margin-bottom:25px; font-size:24px; }
            .form-group { margin-bottom:20px; }
            label { display:block; margin-bottom:8px; font-weight:500; color:#2c3e50; }
            input, select, textarea { width:100%; padding:14px; border:1px solid #ddd; border-radius:12px; font-size:16px; }
            input[type="file"] { padding:8px; }
            .btn { background:#e74c3c; color:white; border:none; border-radius:12px; padding:16px; font-size:18px; font-weight:600; width:100%; margin-top:10px; }
            .btn:active { background:#c0392b; transform:scale(0.98); }
            .tips { background:#fff8e1; padding:15px; border-radius:12px; margin-top:20px; font-size:14px; line-height:1.5; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>✍️ 书法课堂记录</h2>
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="class">班级</label>
                    <select id="class" name="class_name" required>
                        <option value="">请选择班级</option>
                        <option value="一年级楷书基础班">一年级楷书基础班</option>
                        <option value="二年级行书启蒙班">二年级行书启蒙班</option>
                        <option value="三年级创作提升班">三年级创作提升班</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="student">学生姓名</label>
                    <input type="text" id="student" name="student_name" placeholder="例：张明轩" required>
                </div>
                
                <div class="form-group">
                    <label for="posture">书写姿势照片（侧拍）</label>
                    <input type="file" id="posture" name="posture" accept="image/*" capture="environment" required>
                </div>
                
                <div class="form-group">
                    <label for="work">当堂作品照片</label>
                    <input type="file" id="work" name="work" accept="image/*" capture="environment" required>
                </div>
                
                <div class="form-group">
                    <label for="comment">教师评语（可留空，系统将自动生成AI评语）</label>
                    <textarea id="comment" name="comment" rows="3" placeholder="💡 留空时系统自动为您生成个性化点评。或手动输入自己的评语..."></textarea>
                </div>
                
                <div class="tips" style="background:#e8f5e9; margin-bottom:15px;">
                    <strong>💡 AI评语提示</strong><br>
                    • 评语可留空，系统将自动分析作品生成AI点评<br>
                    • 也可手动输入，系统将直接使用您的评语<br>
                    • AI评语温暖、具体，适合家长阅读
                </div>
                
                <button type="submit" class="btn">提交给家长群</button>
            </form>
            
            <div class="tips">
                <strong>📌 温馨提示</strong><br>
                • 姿势照请侧拍，能看清头/肩/背<br>
                • 作品照光线要充足，四角完整<br>
                • 评语越具体，家长越安心
            </div>
        </div>
        
        <script>
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.querySelector('.btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '🤖 正在生成AI评语...';
            btn.disabled = true;
            
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ 上传成功！作品已发送至家长群，学生档案已更新');
                    e.target.reset();
                } else {
                    alert('❌ 失败: ' + result.msg);
                }
            } catch (error) {
                alert('⚠️ 网络错误: ' + error.message);
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        });
        </script>
    </body>
    </html>
    '''
    return html


# ====== 核心 API ======

@app.route("/api/submit", methods=["POST"])
def submit_record():
    """核心API - 处理上传、生成拼图、推送企业微信、保存数据"""
    try:
        # 1. 获取表单数据
        class_name = request.form["class_name"]
        student_name = request.form["student_name"]
        comment = request.form.get("comment", "").strip()  # 允许空值
        posture = request.files["posture"]
        work = request.files["work"]

        # 2. 生成唯一ID和文件名
        uid = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        posture_path = f"{UPLOAD_FOLDER}/p_{uid}.jpg"
        work_path = f"{UPLOAD_FOLDER}/w_{uid}.jpg"
        collage_path = f"{UPLOAD_FOLDER}/c_{uid}.jpg"

        # 3. 保存原始照片
        posture.save(posture_path)
        work.save(work_path)

        # 4. 如果教师没有输入评语，调用AI生成
        ai_comment = None
        ai_model = None
        generation_time_ms = 0
        if not comment or comment.strip() == "":
            ai_comment, ai_error, generation_time_ms = generate_ai_comment(
                work_path, student_name, style="warm"
            )
            if ai_comment:
                comment = ai_comment
                ai_model = "qwen-vl-max"
            else:
                # AI生成失败，使用默认评语
                comment = "今天的书法作品进步很棒！继续加油！"
                generation_time_ms = 0

        # 5. 生成拼图
        collage_success = create_collage(
            posture_path, work_path, collage_path, class_name, student_name, comment
        )
        if not collage_success:
            return jsonify({"success": False, "msg": "拼图生成失败"})

        # 6. 发送到企业微信
        image_url = f"{DOMAIN}/{os.path.basename(collage_path)}"
        success, msg = send_to_wechat(
            collage_path, class_name, student_name, comment, image_url
        )
        if not success:
            return jsonify({"success": False, "msg": f"群推送失败: {msg}"})

        # 7. 保存到本地数据库
        record = {
            "id": uid,
            "class": class_name,
            "student": student_name,
            "comment": comment,
            "ai_generated": ai_comment is not None,
            "comment_length": len(comment),
            "posture_url": f"/{os.path.basename(posture_path)}",
            "work_url": f"/{os.path.basename(work_path)}",
            "collage_url": f"/{os.path.basename(collage_path)}",
            "created_at": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),
            "group": class_name,
        }

        if ai_comment is not None:
            record["ai_model"] = ai_model
            record["generation_time_ms"] = generation_time_ms

        save_record(record)

        return jsonify(
            {
                "success": True,
                "msg": "已发送到家长群！" + ("（AI生成评语）" if ai_comment else ""),
                "record_id": uid,
                "comment": comment,
                "archive_url": f"{DOMAIN}/archive?student={student_name}&class={class_name}",
            }
        )

    except Exception as e:
        logger.error(f"❌ 提交记录失败: {str(e)}")
        return jsonify({"success": False, "msg": str(e)})


# ====== 学生档案页面 ======

@app.route("/archive")
def student_archive():
    """家长查看学生档案页"""
    student_name = request.args.get("student", "")
    class_name = request.args.get("class", "")

    # 加载并过滤记录
    all_records = load_records()
    records = [
        r
        for r in all_records
        if r.get("student") == student_name and r.get("class") == class_name
    ]

    # 按时间倒序排列
    records.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{student_name}的成长档案 - {SCHOOL_NAME}</title>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; font-family:"PingFang SC","Microsoft YaHei",sans-serif; }}
            body {{ background:#f8f9fa; padding:15px; }}
            .header {{ text-align:center; padding:20px 0; background:white; border-radius:16px; margin-bottom:20px; box-shadow:0 2px 10px rgba(0,0,0,0.05); }}
            h1 {{ color:#e74c3c; font-size:24px; }}
            .record {{ background:white; border-radius:16px; padding:20px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }}
            .record-date {{ color:#7f8c8d; font-size:14px; margin-bottom:10px; }}
            .record-img {{ width:100%; border-radius:12px; margin:10px 0; }}
            .record-comment {{ color:#27ae60; font-size:16px; padding:8px 0; }}
            .tips {{ background:#e8f4fd; padding:15px; border-radius:12px; margin-top:20px; font-size:14px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎨 {student_name}的墨香成长</h1>
            <p>{class_name} · 共 {len(records)} 次课堂记录</p>
        </div>
        
        {''.join(f'''
        <div class="record">
            <div class="record-date">{r.get("created_at", "")[:16].replace("T", " ")}</div>
            <img class="record-img" src="{r.get("collage_url", "")}" alt="课堂记录">
            <div class="record-comment">📝 {r.get("comment", "")}</div>
        </div>
        ''' for r in records)}
        
        <div class="tips">
            <strong>💡 小提示</strong><br>
            • 长按图片可保存到手机<br>
            • 点右上角「···」可分享给家人
        </div>
    </body>
    </html>
    '''

    return html


# ====== 统计和导出页面 ======

@app.route("/stats")
def stats_page():
    """统计信息页面"""
    try:
        records = load_records()

        if not records:
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>统计信息</title>
                <style>
                    * { margin:0; padding:0; box-sizing:border-box; font-family:"PingFang SC","Microsoft YaHei",sans-serif; }
                    body { padding:20px; background:#f8f9fa; }
                    .container { max-width:600px; margin:0 auto; background:white; border-radius:16px; padding:25px; box-shadow:0 4px 12px rgba(0,0,0,0.05); }
                    h1 { color:#e74c3c; text-align:center; margin-bottom:20px; }
                    .empty { text-align:center; color:#999; padding:20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📊 统计信息</h1>
                    <div class="empty">暂无数据，请先在上传页提交记录。</div>
                </div>
            </body>
            </html>
            '''

        # 计算统计数据
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [
            r for r in records if r.get("created_at", "").startswith(today)
        ]
        ai_count = sum(1 for r in records if r.get("ai_generated"))

        # 计算最活跃班级
        class_counts = {}
        for r in records:
            class_name = r.get("class", "")
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        most_active_class = (
            max(class_counts.items(), key=lambda x: x[1])
            if class_counts
            else ("", 0)
        )

        # 计算 AI 使用率
        ai_usage_rate = round(ai_count / len(records) * 100, 1) if records else 0

        # 计算平均 AI 评语长度
        ai_records = [r for r in records if r.get("ai_generated")]
        avg_ai_length = (
            round(
                sum(r.get("comment_length", 0) for r in ai_records) / len(ai_records),
                1,
            )
            if ai_records
            else 0
        )

        # 获取所有班级
        all_classes = get_all_classes()
        class_buttons_html = "".join(
            f'<a href="/export?class={quote(cls)}" class="btn btn-secondary" title="导出 {cls}">📤 {cls}</a>'
            for cls in all_classes
        )

        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>统计信息</title>
            <style>
                * {{ margin:0; padding:0; box-sizing:border-box; font-family:"PingFang SC","Microsoft YaHei",sans-serif; }}
                body {{ padding:20px; background:#f8f9fa; }}
                .container {{ max-width:700px; margin:0 auto; }}
                h1 {{ color:#e74c3c; text-align:center; margin-bottom:30px; font-size:28px; }}
                h3 {{ color:#2c3e50; margin-top:25px; margin-bottom:12px; font-size:16px; }}
                .stat-box {{ background:white; border-radius:12px; padding:20px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.05); }}
                .stat-label {{ color:#666; font-size:14px; margin-bottom:8px; }}
                .stat-value {{ color:#2c3e50; font-size:32px; font-weight:600; }}
                .stat-unit {{ color:#999; font-size:14px; margin-left:8px; }}
                .buttons {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:20px; }}
                .btn {{ flex:1; min-width:150px; background:#e74c3c; color:white; border:none; border-radius:8px; padding:12px; font-size:14px; cursor:pointer; text-decoration:none; text-align:center; }}
                .btn:hover {{ background:#c0392b; }}
                .btn-secondary {{ background:#3498db; min-width:auto; flex:0 1 auto; }}
                .btn-secondary:hover {{ background:#2980b9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 统计信息</h1>
                
                <div class="stat-box">
                    <div class="stat-label">今日提交总数</div>
                    <div class="stat-value">{len(today_records)} <span class="stat-unit">条</span></div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-label">AI 使用率</div>
                    <div class="stat-value">{ai_usage_rate} <span class="stat-unit">%</span></div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-label">最活跃班级</div>
                    <div class="stat-value">{most_active_class[0]} <span class="stat-unit">({most_active_class[1]}条)</span></div>
                </div>
                
                <div class="stat-box">
                    <div class="stat-label">平均 AI 评语长度</div>
                    <div class="stat-value">{avg_ai_length} <span class="stat-unit">字</span></div>
                </div>
                
                <h3>按班级导出</h3>
                <div class="buttons">
                    {class_buttons_html}
                </div>
                
                <h3>全量导出</h3>
                <div class="buttons">
                    <a href="/export" class="btn">📋 导出所有记录</a>
                    <a href="/upload" class="btn">📱 返回上传</a>
                </div>
            </div>
        </body>
        </html>
        '''
        return html

    except Exception as e:
        logger.error(f"❌ 统计页面错误: {str(e)}")
        return f"<p>错误: {str(e)}</p>"


@app.route("/export")
def export_csv():
    """CSV 导出接口"""
    try:
        class_name = request.args.get("class")
        date_str = request.args.get("date")

        # URL 解码
        if class_name:
            class_name = unquote(class_name)
        if date_str:
            date_str = unquote(date_str)

        # 筛选记录
        records = filter_records(class_name=class_name, date_str=date_str)

        if not records:
            return jsonify({"error": "没有找到符合条件的记录"}), 400

        # 转换为 CSV
        csv_data = records_to_csv(records)

        # 生成文件名
        if date_str:
            filename = f"classroom_records_{date_str}.csv"
        elif class_name:
            safe_class_name = class_name.replace("/", "_").replace("\\", "_")
            filename = f"classroom_records_{safe_class_name}.csv"
        else:
            filename = f"classroom_records_{datetime.now().strftime('%Y%m%d')}.csv"

        return csv_data, 200, {
            "Content-Type": "text/csv; charset=utf-8",
            'Content-Disposition': f'attachment; filename="{filename}"',
        }

    except Exception as e:
        logger.error(f"❌ CSV 导出失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ====== 静态文件服务 ======

@app.route("/<path:filename>")
def serve_file(filename):
    """提供上传的图片文件"""
    if filename.endswith(".jpg"):
        return send_from_directory(UPLOAD_FOLDER, filename)
    return "文件不存在", 404


# ====== 应用启动 ======

if __name__ == "__main__":
    logger.info("\n🚀 雅趣智能课堂反馈MVP已启动！")
    logger.info(f"📱 教师上传地址: {DOMAIN}/upload")
    logger.info("📁 💡 请通过公网IP访问,非 localhost")
    logger.info("⚠️ 重要部署提示 (首次运行后):")
    logger.info("1. 申请企业微信机器人: 群主在企业微信→群→右上角···→群机器人→添加")
    logger.info("2. 替换代码中的 WECHAT_WEBHOOK 为您的机器人地址")
    logger.info("3. 将 DOMAIN 改为您的服务器公网IP或域名")
    logger.info("4. 云服务器需开放 5000 端口 (安全组规则)")

    app.run(host="0.0.0.0", port=5000, debug=False)
