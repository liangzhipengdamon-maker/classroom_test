"""
数据管理模块 - 记录加载、筛选、导出

功能职责：
- load_records() - 从 JSON 加载记录
- filter_records() - 按班级/日期筛选
- records_to_csv() - 转换为 CSV 格式
- save_record() - 保存单条记录到文件
"""

import os
import json
import csv
import logging
from io import StringIO
from .config import RECORDS_FILE

logger = logging.getLogger(__name__)


def load_records(db_path=RECORDS_FILE):
    """统一读取 records.json 文件

    Args:
        db_path: 记录文件路径

    Returns:
        记录列表
    """
    if not os.path.exists(db_path):
        logger.info(f"ℹ️ 记录文件不存在: {db_path}")
        return []

    try:
        with open(db_path, "r", encoding="utf-8") as f:
            records = json.load(f)
            logger.info(f"✅ 成功加载 {len(records)} 条记录")
            return records
    except Exception as e:
        logger.error(f"❌ 读取记录失败: {str(e)}")
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
        result = [r for r in result if r.get("class") == class_name]
        logger.info(f"按班级筛选: {class_name} -> {len(result)} 条记录")

    if date_str:
        result = [r for r in result if r.get("created_at", "").startswith(date_str)]
        logger.info(f"按日期筛选: {date_str} -> {len(result)} 条记录")

    return result


def records_to_csv(records):
    """将记录转换为 CSV 字符串

    Args:
        records: 记录数组

    Returns:
        CSV 字符串
    """
    csv_output = StringIO()
    fieldnames = [
        "时间",
        "班级",
        "学生姓名",
        "评语类型",
        "评语内容",
        "评语长度",
        "生成耗时(ms)",
    ]
    writer = csv.DictWriter(csv_output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for record in records:
        row = {
            "时间": record.get("created_at", "")[:16],
            "班级": record.get("class", ""),
            "学生姓名": record.get("student", ""),
            "评语类型": "AI" if record.get("ai_generated") else "手动",
            "评语内容": record.get("comment", ""),
            "评语长度": record.get("comment_length", 0),
            "生成耗时(ms)": (
                record.get("generation_time_ms", "-")
                if record.get("ai_generated")
                else "-"
            ),
        }
        writer.writerow(row)

    logger.info(f"✅ 成功转换 {len(records)} 条记录为 CSV")
    return csv_output.getvalue()


def save_record(record, db_path=RECORDS_FILE):
    """保存单条记录到文件

    Args:
        record: 记录字典
        db_path: 记录文件路径

    Returns:
        bool: 保存是否成功
    """
    try:
        records = load_records(db_path)
        records.append(record)

        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 记录保存成功: {record.get('id')}")
        return True
    except Exception as e:
        logger.error(f"❌ 保存记录失败: {str(e)}")
        return False


def get_all_classes():
    """获取所有班级列表

    Returns:
        班级名称列表（已排序）
    """
    records = load_records()
    classes = sorted(
        list(set(r.get("class", "") for r in records if r.get("class")))
    )
    return classes
