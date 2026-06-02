#!/usr/bin/env python3
"""
Excel去重工具
按 UI ID + 标注员 分组，保留提交时间最晚的记录
"""

import pandas as pd
import os
from datetime import datetime


def deduplicate_by_ui_annotator(
    input_file: str,
    output_file: str = None,
    ui_id_column: str = "UI ID",
    annotator_column: str = "标注员",
    submit_time_column: str = "提交时间"
) -> str:
    """
    读取Excel文件，按 UI ID + 标注员 去重，保留提交时间最晚的记录

    Args:
        input_file: 输入Excel文件路径
        output_file: 输出Excel文件路径，默认为 input_file 加上 "_dedup" 后缀
        ui_id_column: UI ID所在的列名（默认为 "UI ID"）
        annotator_column: 标注员所在的列名（默认为 "标注员"）
        submit_time_column: 提交时间所在的列名（默认为 "提交时间"）

    Returns:
        保存的输出文件路径
    """
    # 设置默认输出文件名
    if output_file is None:
        file_name, file_ext = os.path.splitext(input_file)
        output_file = f"{file_name}_dedup{file_ext}"

    # 读取Excel文件
    print(f"正在读取Excel文件: {input_file}")
    df = pd.read_excel(input_file)
    original_count = len(df)
    print(f"  原始行数: {original_count}")

    # 检查必要的列是否存在
    required_cols = [ui_id_column, annotator_column, submit_time_column]
    for col in required_cols:
        if col not in df.columns:
            available_cols = ', '.join(str(c) for c in df.columns.tolist())
            raise ValueError(f"列 '{col}' 不存在。可用列: {available_cols}")

    # 转换提交时间为datetime类型（如果不是的话）
    print(f"正在处理时间格式...")
    df[submit_time_column] = pd.to_datetime(df[submit_time_column])

    # 按 UI ID + 标注员 分组，保留提交时间最晚的记录
    print(f"正在按 '{ui_id_column}' + '{annotator_column}' 去重...")
    print(f"  保留规则: 提交时间最晚的记录")

    # 排序后去重：先按分组列排序，再按提交时间倒序，然后取每组第一条
    df_sorted = df.sort_values(
        by=[ui_id_column, annotator_column, submit_time_column],
        ascending=[True, True, False]  # 提交时间倒序
    )

    # 去重（keep='first' 保留排序后的第一条，即时间最晚的）
    df_dedup = df_sorted.drop_duplicates(
        subset=[ui_id_column, annotator_column],
        keep='first'
    )

    dedup_count = len(df_dedup)
    removed_count = original_count - dedup_count

    print(f"  去重后行数: {dedup_count}")
    print(f"  删除重复: {removed_count}")
    print(f"  重复率: {removed_count/original_count*100:.1f}%")

    # 显示被删除的重复记录详情
    if removed_count > 0:
        print(f"\n重复记录统计:")
        duplicates = df.groupby([ui_id_column, annotator_column]).size().reset_index(name='count')
        duplicates = duplicates[duplicates['count'] > 1].sort_values('count', ascending=False)
        for _, row in duplicates.head(10).iterrows():
            print(f"  {row[ui_id_column]} + {row[annotator_column]}: {row['count']}条 -> 保留1条，删除{row['count']-1}条")
        if len(duplicates) > 10:
            print(f"  ... 还有 {len(duplicates)-10} 组重复")

    # 保存到新的Excel文件
    print(f"\n正在保存到: {output_file}")
    df_dedup.to_excel(output_file, index=False)
    print("完成!")

    return output_file


def main():
    """主函数：处理默认的Excel文件"""
    import os

    # 默认文件路径（相对于项目根目录）
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(base_dir, "export-ej_1780043739514_g4l9kg_replaced.xlsx")

    if not os.path.exists(input_file):
        print(f"错误: 找不到文件 {input_file}")
        print("请确保Excel文件存在于项目根目录中")
        return

    output_file = deduplicate_by_ui_annotator(input_file)
    print(f"\n输出文件: {output_file}")


if __name__ == "__main__":
    main()
