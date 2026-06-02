# ID映射字典：Excel Task ID -> Question ID
# 根据question内容匹配建立

TASK_ID_TO_QUESTION_ID = {
    # Desktop 任务 (数字ID)
    "T58": "117",   # 科学家互动平台
    "T60": "316",   # 读书俱乐部平台
    "T25": "81",    # 法语学习应用
    "T37": "611",   # 大学生免费资源网站
    "T22": "197",   # API管理仪表板
    "T47": "490",   # MASCOTAPPS宠物应用
    "T44": "296",   # 商务鞋营销网站
    "T38": "451",   # 美发沙龙网站
    "T21": "97",    # 数字银行平台
    "T63": "439",   # 慢性病管理应用
    "T34": "250",   # 活动票务应用
    "T31": "840",   # 同人小说门户
    "T29": "285",   # 类Twitter社交平台
    "T49": "633",   # 类Notion课堂笔记
    "T35": "437",   # 待办事项网站
    "T66": "395",   # 风投公司主页
    "T50": "259",   # 手表店结账界面
    "T54": "782",   # 电脑销售网站
    "T51": "825",   # NBA新闻网站
    "T24": "705",   # 火星天气应用
    "T64": "643",   # 复合增长可视化
    "T61": "252",   # 杭州探索网站
    "T48": "582",   # 邓稼先研究展示
    "T20": "58",    # 泰国餐厅主页
    "T69": "77",    # 快餐公司主页

    # Mobile - 实用工具 (U系列)
    "T42": "U001",  # 家庭账单记录
    "T46": "U002",  # AA记账器
    "T53": "U003",  # 旅行Packing List
    "T59": "U004",  # 旅行规划
    "T65": "U005",  # 爸妈用药提醒
    "T26": "U006",  # 晚餐抽签器
    "T32": "U007",  # 宠物成长日记
    "T56": "U008",  # 心情日记

    # Mobile - 教育学习 (E系列)
    "T45": "E001",  # 雅思单词打卡
    "T41": "E002",  # 少儿英语拼读
    "T39": "E003",  # 考研政治刷题
    "T30": "E004",  # 智能错题本
    "T27": "E005",  # 光的折射演示
    "T67": "E006",  # 模拟面试官

    # Mobile - 休闲游戏 (G系列)
    "T62": "G001",  # 飞机大战
    "T23": "G002",  # 贪吃蛇
    "T33": "G003",  # 像素画生成器
    "T36": "G004",  # 情绪减压工具
    "T43": "G005",  # 电子木鱼

    # Mobile - 办公效率 (W系列)
    "T28": "W001",  # 待办清单
    "T68": "W002",  # 倒计时工具
    "T57": "W003",  # 番茄钟
    "T55": "W004",  # 会议纪要整理

    # Mobile - 健康管理 (H系列)
    "T40": "H001",  # 卡路里计算器
    "T52": "H002",  # 喝水提醒
}


def add_question_id_to_excel(
    input_file: str,
    output_file: str = None,
    task_id_column: str = "Task ID",
    ui_id_column: str = "UI ID"
) -> str:
    """
    读取Excel文件，将Task ID和UI ID替换为Question ID格式，并保存新文件

    Args:
        input_file: 输入Excel文件路径
        output_file: 输出Excel文件路径，默认为 input_file 加上 "_replaced" 后缀
        task_id_column: Task ID所在的列名（默认为 "Task ID"）
        ui_id_column: UI ID所在的列名（默认为 "UI ID"）

    Returns:
        保存的输出文件路径
    """
    import pandas as pd
    import os
    import re

    # 设置默认输出文件名
    if output_file is None:
        file_name, file_ext = os.path.splitext(input_file)
        output_file = f"{file_name}_replaced{file_ext}"

    # 读取Excel文件（使用默认方式，第一行作为表头）
    print(f"正在读取Excel文件: {input_file}")
    df = pd.read_excel(input_file)
    print(f"  列名: {list(df.columns)}")

    # 检查必要的列是否存在
    if task_id_column not in df.columns:
        available_cols = ', '.join(str(c) for c in df.columns.tolist())
        raise ValueError(f"列 '{task_id_column}' 不存在。可用列: {available_cols}")
    if ui_id_column not in df.columns:
        available_cols = ', '.join(str(c) for c in df.columns.tolist())
        raise ValueError(f"列 '{ui_id_column}' 不存在。可用列: {available_cols}")

    # 1. 替换 Task ID 列
    print(f"正在替换 '{task_id_column}' 列...")
    df[task_id_column] = df[task_id_column].map(TASK_ID_TO_QUESTION_ID)

    # 统计Task ID映射情况
    mapped_count = df[task_id_column].notna().sum()
    total_count = len(df)
    print(f"  - Task ID 替换: {mapped_count}/{total_count}")

    # 2. 替换 UI ID 列（格式如 T58_1 -> question_id_1）
    print(f"正在替换 '{ui_id_column}' 列...")

    def replace_ui_id(ui_id):
        """将 UI ID 从 T58_1 格式替换为 question_id_1 格式"""
        if pd.isna(ui_id):
            return ui_id
        ui_id_str = str(ui_id)
        # 匹配 T58_1 格式（T+数字+_+数字）
        match = re.match(r'^(T\d+)_(\d+)$', ui_id_str)
        if match:
            task_id = match.group(1)  # T58
            suffix = match.group(2)   # 1
            question_id = TASK_ID_TO_QUESTION_ID.get(task_id)
            if question_id:
                return f"{question_id}_{suffix}"
        return ui_id

    df[ui_id_column] = df[ui_id_column].apply(replace_ui_id)
    ui_mapped_count = df[ui_id_column].notna().sum()
    print(f"  - UI ID 替换: 完成")

    # 保存到新的Excel文件
    print(f"正在保存到: {output_file}")
    df.to_excel(output_file, index=False)
    print("完成!")

    return output_file





def task_id_to_question_id(task_id: str) -> str | None:
    """
    将Excel中的Task ID转换为Question.jsonl中的Question ID

    Args:
        task_id: Excel中的Task ID (如 "T58", "T42" 等)

    Returns:
        Question.jsonl中对应的ID (如 "117", "U001" 等)
        如果找不到对应关系，返回None
    """
    return TASK_ID_TO_QUESTION_ID.get(task_id)


def question_id_to_task_id(question_id: str) -> str | None:
    """
    将Question.jsonl中的Question ID转换为Excel中的Task ID

    Args:
        question_id: Question.jsonl中的ID (如 "117", "U001" 等)

    Returns:
        Excel中对应的Task ID (如 "T58", "T42" 等)
        如果找不到对应关系，返回None
    """
    reverse_mapping = {v: k for k, v in TASK_ID_TO_QUESTION_ID.items()}
    return reverse_mapping.get(question_id)


def get_all_mappings() -> dict[str, str]:
    """
    获取所有Task ID到Question ID的映射关系

    Returns:
        包含所有映射关系的字典
    """
    return TASK_ID_TO_QUESTION_ID.copy()

def main():
    """主函数：处理默认的Excel文件"""
    import os

    # 默认文件路径（相对于项目根目录）
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(base_dir, "export-ej_1780043739514_g4l9kg.xlsx")

    if not os.path.exists(input_file):
        print(f"错误: 找不到文件 {input_file}")
        print("请确保Excel文件存在于项目根目录中")
        return

    output_file = add_question_id_to_excel(input_file)
    print(f"\n输出文件: {output_file}")

    
if __name__ == "__main__":
    import sys

    # 如果有命令行参数 --test，则运行测试
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 测试映射关系
        print("Task ID -> Question ID 映射示例:")
        print("-" * 50)

        test_cases = ["T58", "T42", "T45", "T62", "T28", "T40", "T60"]
        for task_id in test_cases:
            question_id = task_id_to_question_id(task_id)
            print(f"  {task_id} -> {question_id}")

        print("\n" + "=" * 50)
        print(f"总共建立了 {len(TASK_ID_TO_QUESTION_ID)} 条映射关系")
    else:
        # 默认运行Excel处理
        main()
