# class_mvp.py —— 雅趣智能课堂反馈系统（教师上传+家长群推送+学生档案）
# 依赖安装: pip install flask pillow requests
# 运行命令: python class_mvp.py
# 访问地址: http://您的服务器IP:5000/upload （教师上传页）
DOMAIN = "https://class.cangfengge.com"

from flask import Flask, request, render_template_string, send_from_directory, jsonify
from PIL import Image, ImageDraw, ImageFont
import os, time, uuid, json, base64, hashlib, csv, logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from dashscope import MultiModalConversation
from io import StringIO

load_dotenv()
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ▶▶▶【关键配置】您只需修改这3行 ▶▶▶
WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=51a874dd-0727-4ce9-895e-8b090a4c3536"  # 1. 企业微信机器人地址
SCHOOL_NAME = "雅趣堂书画"  # 2. 您的机构名称（显示在水印中）
DOMAIN = "https://class.cangfengge.com"  # 3. 服务器公网地址（部署后改为您的IP或域名）
# ▶▶▶ 配置结束 ▶▶▶

# 🤖 AI 评语生成函数（调用通义千问 Qwen-VL）
def generate_ai_comment(image_path, student_name="学生"):
    """调用 Qwen-VL 多模态大模型，根据书法作品生成评语
    
    Args:
        image_path: 书法作品照片路径
        student_name: 学生名字（用于日志记录）
    
    Returns:
        (comment, error, elapsed_ms): 成功返回(评语文本, None, 耗时ms)，失败返回(None, 错误信息, 0)
    """
    MAX_RETRIES = 2  # 最多重试2次
    RETRY_DELAY = 1  # 重试延迟1秒
    
    if not DASHSCOPE_API_KEY:
        return None, "API Key 未配置", 0
    
    for attempt in range(MAX_RETRIES):
        try:
            # 第一次尝试时打印日志
            if attempt == 0:
                print(f"🔍 正在为 {student_name} 调用 Qwen-VL...")
            else:
                print(f"🔄 重试第 {attempt} 次调用 Qwen-VL...")
            
            start_time = time.time()
            
            # 构建消息体
            messages = [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'image': image_path  # 支持本地文件路径或URL
                        },
                        {
                            'type': 'text',
                            'text': '请根据这张书法作品，给出一段温暖、具体的评语，适合家长阅读。评语应该包括：(1)正面评价点，(2)可改进的地方，(3)鼓励语言。'
                        }
                    ]
                }
            ]
            
            # 调用 Qwen-VL 多模态对话 API
            response = MultiModalConversation.call(
                model='qwen-vl-max',
                messages=messages,
                api_key=DASHSCOPE_API_KEY
            )
            
            # 检查响应
            if response.status_code == 200:
                # 提取生成的评语
                comment = response.output.choices[0].message.content
                # 如果是列表，取第一个文本内容
                if isinstance(comment, list):
                    for item in comment:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            comment = item.get('text', '')
                            break
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                print(f"✅ AI 评语生成成功（耗时 {elapsed_ms}ms）")
                return str(comment), None, elapsed_ms
            else:
                error_msg = response.message if hasattr(response, 'message') else '未知错误'
                print(f"⚠️ AI 调用失败 (HTTP {response.status_code}): {error_msg}")
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    return None, f"AI 调用失败: {error_msg}", 0
        
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            print(f"⚠️ AI 调用异常 ({error_type}): {error_msg}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < MAX_RETRIES - 1:
                print(f"   将在 {RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                return None, "AI 评语生成暂时不可用，请稍后重试，或手动填写评语。", 0
    
    # 如果所有重试都失败
    return None, "AI 评语生成暂时不可用，请稍后重试，或手动填写评语。", 0

# 📱 教师手机端上传页面（极简设计，专为手机浏览器优化）
@app.route('/upload')
def upload_page():
    return render_template_string('''
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
    ''')

# 🚀 核心API：处理上传、生成拼图、推送到企业微信
@app.route('/api/submit', methods=['POST'])
def submit_record():
    try:
        # 1. 获取表单数据
        class_name = request.form['class_name']
        student_name = request.form['student_name']
        comment = request.form.get('comment', '').strip()  # 使用 .get() 允许空值
        posture = request.files['posture']
        work = request.files['work']
        
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
        if not comment or comment.strip() == '':
            # 调用AI基于作品照片生成评语，传入学生名字用于日志记录
            ai_comment, ai_error, generation_time_ms = generate_ai_comment(work_path, student_name)
            if ai_comment:
                comment = ai_comment
                ai_model = "qwen-vl-max"  # 标记 AI 模型
            else:
                # AI生成失败，使用嘘底默认评语
                comment = "今天的书法作品进步很棒！继续加油！"
                generation_time_ms = 0
        
        # 5. 生成拼图（专为书法优化的排版）
        create_collage(posture_path, work_path, collage_path, class_name, student_name, comment)
        
        # 6. 发送到企业微信（家长群）
        image_url = f"{DOMAIN}/{os.path.basename(collage_path)}"
        success, msg = send_to_wechat(collage_path, class_name, student_name, comment, image_url)
        
        if not success:
            return jsonify({"success": False, "msg": f"群推送失败: {msg}"})
        
        # 7. 保存到本地数据库（SQLite太重，用JSON文件实现）
        record = {
            "id": uid,
            "class": class_name,
            "student": student_name,
            "comment": comment,
            "ai_generated": ai_comment is not None,  # 标记是否为AI生成
            "comment_length": len(comment),  # 评语字符数
            "posture_url": f"/{os.path.basename(posture_path)}",
            "work_url": f"/{os.path.basename(work_path)}",
            "collage_url": f"/{os.path.basename(collage_path)}",
            "created_at": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat(),  # ISO 8601时间戳
            "group": class_name  # 用于区分班级群
        }
        
        # 如果是AI生成，添加AI爳类信息
        if ai_comment is not None:
            record["ai_model"] = ai_model
            record["generation_time_ms"] = generation_time_ms
        
        # 简易数据存储（实际生产环境建议用SQLite）
        db_path = "records.json"
        records = []
        if os.path.exists(db_path):
            with open(db_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
        records.append(record)
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "msg": "已发送到家长群！" + ("（AI生成评语）" if ai_comment else ""),
            "record_id": uid,
            "comment": comment,
            "archive_url": f"{DOMAIN}/archive?student={student_name}&class={class_name}"
        })
    
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

# 📑 数据分析与统计核心函数
def load_records(db_path="records.json"):
    """统一读取 records.json 文件"""
    if not os.path.exists(db_path):
        return []
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 读取记录失败: {str(e)}")
        return []

def filter_records(class_name=None, date_str=None):
    """按条件筛选记录
    
    Args:
        class_name: 班级名称，为None表示不筛选
        date_str: 日期（格式 YYYY-MM-DD），为None表示不筛选
    
    Returns:
        筛选后的记录数组
    """
    records = load_records()
    result = records
    
    if class_name:
        result = [r for r in result if r.get('class') == class_name]
    
    if date_str:
        result = [r for r in result if r.get('created_at', '').startswith(date_str)]
    
    return result

def records_to_csv(records):
    """将记录不称。CSV字符串
    
    Args:
        records: 记录数组
    
    Returns:
        CSV字符串
    """
    csv_output = StringIO()
    fieldnames = ["时间", "班级", "学生姓名", "评语类型", "评语内容", "评语长度", "生成耗时(ms)"]
    writer = csv.DictWriter(csv_output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    
    for record in records:
        row = {
            '时间': record.get('created_at', '')[:16],
            '班级': record.get('class', ''),
            '学生姓名': record.get('student', ''),
            '评语类型': 'AI' if record.get('ai_generated') else '手动',
            '评语内容': record.get('comment', ''),
            '评语长度': record.get('comment_length', 0),
            '生成耗时(ms)': record.get('generation_time_ms', '-') if record.get('ai_generated') else '-'
        }
        writer.writerow(row)
    
    return csv_output.getvalue()

# 🖼️ 生成书法专用拼图（含姿势+作品+评语+水印）
def create_collage(posture_path, work_path, output_path, class_name, student_name, comment):
    # 加载并调整图片尺寸
    posture_img = Image.open(posture_path).convert("RGB")
    work_img = Image.open(work_path).convert("RGB")
    
    # 统一宽度（手机竖屏友好）
    target_width = 750
    posture_ratio = target_width / posture_img.width
    work_ratio = target_width / work_img.width
    
    posture_img = posture_img.resize((target_width, int(posture_img.height * posture_ratio)), Image.LANCZOS)
    work_img = work_img.resize((target_width, int(work_img.height * work_ratio)), Image.LANCZOS)
    
    # 创建拼图画布（高度=姿势高+作品高+底部文字区）
    total_height = posture_img.height + work_img.height + 250
    collage = Image.new("RGB", (target_width, total_height), "#ffffff")
    
    # 粘贴图片
    collage.paste(posture_img, (0, 0))
    collage.paste(work_img, (0, posture_img.height))
    
    # 添加文字（使用系统字体，避免中文乱码）
    draw = ImageDraw.Draw(collage)
    try:
        font_large = ImageFont.truetype("simhei.ttf", 36)  # Windows
    except:
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 36)  # Mac
        except:
            font_large = ImageFont.load_default()

    try:
        font_small = ImageFont.truetype("simhei.ttf", 28)
    except:
        font_small = ImageFont.load_default()
    
    # 课次信息
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    course_info = f"{now} | {class_name}"
    draw.text((30, posture_img.height + work_img.height + 20), course_info, fill="#2c3e50", font=font_small)
    
    # 学生评语
    draw.text((30, posture_img.height + work_img.height + 60), f"📝 {student_name}：{comment}", 
              fill="#27ae60", font=font_large)
    
    # 机构水印
    watermark = f"雅趣堂｜{SCHOOL_NAME}"
    draw.text((30, posture_img.height + work_img.height + 120), watermark, fill="#95a5a6", font=font_small)
    
    # 保存
    collage.save(output_path, quality=95, optimize=True)

# 💬 发送到企业微信（家长群）
def send_to_wechat(image_path, class_name, student_name, comment, image_url):
    try:
        # 企业微信要求：图片需先上传到其服务器（我们简化：直接发卡片+图片链接）
        msg_data = {
            "msgtype": "news",
            "news": {
                "articles": [
                    {
                        "title": f"【课堂记录】{student_name} ({class_name})",
                        "description": comment,
                        "url": image_url,
                        "picurl": image_url
                    }
                ]
            }
        }
        
        response = requests.post(WECHAT_WEBHOOK, json=msg_data, timeout=10)
        result = response.json()
        
        if result.get('errcode') == 0:
            return True, "已发送到家长群"
        else:
            return False, result.get('errmsg', '未知错误')
    
    except Exception as e:
        return False, str(e)

# 📂 静态文件服务（图片、档案页）
@app.route('/<path:filename>')
def serve_file(filename):
    if filename.endswith('.jpg'):
        return send_from_directory(UPLOAD_FOLDER, filename)
    return "文件不存在", 404

# 👨‍👩‍👧 家长查看学生档案页
@app.route('/archive')
def student_archive():
    student_name = request.args.get('student', '')
    class_name = request.args.get('class', '')
    
    # 从简易数据库加载记录
    records = []
    if os.path.exists("records.json"):
        with open("records.json", 'r', encoding='utf-8') as f:
            all_records = json.load(f)
            # 过滤当前学生
            records = [r for r in all_records 
                      if r['student'] == student_name and r['class'] == class_name]
    
    # 按时间倒序排列
    records.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ student_name }}的成长档案 - {{ SCHOOL_NAME }}</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; font-family:"PingFang SC","Microsoft YaHei",sans-serif; }
            body { background:#f8f9fa; padding:15px; }
            .header { text-align:center; padding:20px 0; background:white; border-radius:16px; margin-bottom:20px; box-shadow:0 2px 10px rgba(0,0,0,0.05); }
            h1 { color:#e74c3c; font-size:24px; }
            .record { background:white; border-radius:16px; padding:20px; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }
            .record-date { color:#7f8c8d; font-size:14px; margin-bottom:10px; }
            .record-img { width:100%; border-radius:12px; margin:10px 0; }
            .record-comment { color:#27ae60; font-size:16px; padding:8px 0; }
            .tips { background:#e8f4fd; padding:15px; border-radius:12px; margin-top:20px; font-size:14px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎨 {{ student_name }}的墨香成长</h1>
            <p>{{ class_name }} · 共 {{ records|length }} 次课堂记录</p>
        </div>
        
        {% for record in records %}
        <div class="record">
            <div class="record-date">{{ record.created_at[:16].replace('T', ' ') }}</div>
            <img class="record-img" src="{{ record.collage_url }}" alt="课堂记录">
            <div class="record-comment">📝 {{ record.comment }}</div>
        </div>
        {% endfor %}
        
        <div class="tips">
            <strong>💡 小提示</strong><br>
            • 长按图片可保存到手机<br>
            • 点右上角「···」可分享给家人
        </div>
    </body>
    </html>
    ''', student_name=student_name, class_name=class_name, records=records, SCHOOL_NAME=SCHOOL_NAME)

# 📊 统计信息事务上云 /stats
@app.route('/stats')
def stats_page():
    """统计信息事务上云（HTML页面）"""
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
        today_records = [r for r in records if r.get('created_at', '').startswith(today)]
        ai_count = sum(1 for r in records if r.get('ai_generated'))
        
        # 计算最活跃班级
        class_counts = {}
        for r in records:
            class_name = r.get('class', '')
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        most_active_class = max(class_counts.items(), key=lambda x: x[1]) if class_counts else ("", 0)
        
        # 计算 AI 使用率
        ai_usage_rate = round(ai_count / len(records) * 100, 1) if records else 0
        
        # 计算平均 AI 评语长度
        ai_records = [r for r in records if r.get('ai_generated')]
        avg_ai_length = round(sum(r.get('comment_length', 0) for r in ai_records) / len(ai_records), 1) if ai_records else 0
        
        # 获取所有班级列表
        all_classes = sorted(list(set(r.get('class', '') for r in records if r.get('class'))))
        
        # 构建班级导出按钮 HTML（需要 URL 编码班级名称）
        from urllib.parse import quote
        class_buttons_html = ''.join(
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
        return f"<p>错误: {str(e)}</p>"

# 📋 CSV 导出接口 /export
@app.route('/export')
def export_csv():
    """\u5bfc出 CSV 文件，\u652f\u6301\u6309\u73ed\u7ea7\u6216\u65e5\u671f\u7b5b\u9009"""
    try:
        from urllib.parse import unquote
        
        class_name = request.args.get('class')
        date_str = request.args.get('date')
        
        # \u8fdb\u884c URL \u89e3\u7801，\u5e76\u9a8c\u8bc1\u53c2\u6570
        if class_name:
            class_name = unquote(class_name)
        if date_str:
            date_str = unquote(date_str)
        
        # \u7b5b\u9009\u8bb0\u5f55
        records = filter_records(class_name=class_name, date_str=date_str)
        
        if not records:
            return jsonify({"error": "\u6ca1\u6709\u627e\u5230\u7b26\u5408\u6761\u4ef6\u7684\u8bb0\u5f55"}), 400
        
        # \u751f\u6210 CSV
        csv_data = records_to_csv(records)
        
        # \u751f\u6210\u6587\u4ef6\u540d
        if date_str:
            filename = f"classroom_records_{date_str}.csv"
        elif class_name:
            # CSV \u6587\u4ef6\u540d\u4e2d\u7f16\u7801\u4e2d\u6587为 \u6807\u51c6\u5b57\u8282
            safe_class_name = class_name.replace('/', '_').replace('\\', '_')
            filename = f"classroom_records_{safe_class_name}.csv"
        else:
            filename = f"classroom_records_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # \u8fd4\u56de CSV \u6587\u4ef6
        return csv_data, 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"CSV \u5bfc\u51fa\u5931\u8d25: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 🏠 首页（重定向到上传页）
@app.route('/')
def home():
    return '<script>window.location.href="/upload"</script>'

if __name__ == '__main__':
    print(f"\n🚀 雅趣智能课堂反馈MVP已启动！")
    print(f"📱 教师上传地址: {DOMAIN}/upload")
    print(f"📁 💡 请通过公网IP访问,非 localhost")
    print("⚠️ 重要部署提示 (首次运行后):")
    print("1. 申请企业微信机器人: 群主在企业微信→群→右上角···→群机器人→添加")
    print("2. 替换代码中的 WECHAT_WEBHOOK 为您的机器人地址")
    print("3. 将 DOMAIN 改为您的服务器公网IP或域名")
    print("4. 云服务器需开放 5000 端口 (安全组规则)")
    
    app.run(host='0.0.0.0', port=5000, debug=False)