#!/usr/bin/env python3
"""
分析 pairwise_results.json，生成模型胜负统计和评分报告
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path


def normalize_model_name(name):
    """将模型名称中的 . 替换为 -，避免 JSON 键解析问题"""
    return name.replace(".", "-") if name else name


def load_questions(data_file):
    """加载问题列表，获取每个问题的 class (Mobile/Desktop)"""
    questions = {}
    with open(data_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                q = json.loads(line)
                qid = q.get("ID") or q.get("id")
                questions[qid] = q.get("class", "Mobile")
    return questions


def load_results(results_file):
    """加载评估结果"""
    with open(results_file, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_results(results, questions, model_list, model_list_normalized):
    """
    分析结果，统计每个模型对其他模型的胜负
    
    规则：
    - 每对模型在多个问题上比较，谁赢的问题多，谁就获得这场对决的 W
    - 基础分 1 分
    - 战胜对手得 1 分，平局得 0.5 分
    """
    
    # 创建原始名称到规范化名称的映射
    model_name_map = {orig: norm for orig, norm in zip(model_list, model_list_normalized)}
    
    # 统计结构：{model_a: {model_b: {"wins": 0, "losses": 0, "draws": 0, "total": 0, "mobile_wins": 0, "desktop_wins": 0, "mobile_total": 0, "desktop_total": 0}}}
    head_to_head = defaultdict(lambda: defaultdict(lambda: {
        "wins": 0, "losses": 0, "draws": 0, "total": 0,
        "mobile_wins": 0, "desktop_wins": 0,
        "mobile_total": 0, "desktop_total": 0
    }))
    
    # 处理每条结果
    for result in results:
        if result.get("status") != "success":
            continue
        
        # 使用规范化后的模型名称
        model_a = model_name_map.get(result["model_a"], normalize_model_name(result["model_a"]))
        model_b = model_name_map.get(result["model_b"], normalize_model_name(result["model_b"]))
        qid = result["id"]
        winner = result.get("winner", "")
        # 优先从 result 中获取 class，如果不存在则从 questions 文件加载
        qclass = result.get("class") or questions.get(qid, "Mobile")
        
        # 更新统计
        stats = head_to_head[model_a][model_b]
        reverse_stats = head_to_head[model_b][model_a]
        
        stats["total"] += 1
        reverse_stats["total"] += 1
        
        if qclass == "Mobile":
            stats["mobile_total"] += 1
            reverse_stats["mobile_total"] += 1
        else:
            stats["desktop_total"] += 1
            reverse_stats["desktop_total"] += 1
        
        if winner == "A":
            stats["wins"] += 1
            reverse_stats["losses"] += 1
            if qclass == "Mobile":
                stats["mobile_wins"] += 1
            else:
                stats["desktop_wins"] += 1
        elif winner == "B":
            stats["losses"] += 1
            reverse_stats["wins"] += 1
            if qclass == "Mobile":
                reverse_stats["mobile_wins"] += 1
            else:
                reverse_stats["desktop_wins"] += 1
        else:
            # 平局或其他情况
            stats["draws"] += 1
            reverse_stats["draws"] += 1
    
    # 生成最终汇总
    summary = []
    
    for model_norm in model_list_normalized:
        row = {"model": model_norm}
        
        # 对每个其他模型，判断整体胜负
        total_score = 1.0  # 基础分
        mobile_score = 1.0
        desktop_score = 1.0
        
        for opponent_norm in model_list_normalized:
            if model_norm == opponent_norm:
                row[opponent_norm] = "-"
                continue
            
            stats = head_to_head[model_norm][opponent_norm]
            
            if stats["total"] == 0:
                # 没有对战记录
                row[opponent_norm] = "-"
                continue
            
            # 判断胜负：赢的问题多就是 W
            if stats["wins"] > stats["losses"]:
                row[opponent_norm] = "W"
                total_score += 1.0
            elif stats["wins"] < stats["losses"]:
                row[opponent_norm] = "L"
                # 不得分
            else:
                row[opponent_norm] = "D"  # 平局
                total_score += 0.5
            
            # 分别计算移动端和桌面端得分
            mobile_total = stats["mobile_total"]
            if mobile_total > 0:
                mobile_wins = stats["mobile_wins"]
                mobile_losses = mobile_total - mobile_wins - (stats["draws"] if stats["mobile_total"] > 0 else 0)
                # 简化计算：直接用 mobile_wins vs 对手在 mobile 上的 wins
                opponent_stats = head_to_head[opponent_norm][model_norm]
                opponent_mobile_wins = opponent_stats["mobile_wins"]
                if mobile_wins > opponent_mobile_wins:
                    mobile_score += 1.0
                elif mobile_wins < opponent_mobile_wins:
                    pass  # 不得分
                else:
                    mobile_score += 0.5
            
            desktop_total = stats["desktop_total"]
            if desktop_total > 0:
                opponent_stats = head_to_head[opponent_norm][model_norm]
                opponent_desktop_wins = opponent_stats["desktop_wins"]
                desktop_wins = stats["desktop_wins"]
                if desktop_wins > opponent_desktop_wins:
                    desktop_score += 1.0
                elif desktop_wins < opponent_desktop_wins:
                    pass  # 不得分
                else:
                    desktop_score += 0.5
        
        row["total_score"] = round(total_score, 1)
        row["mobile_score"] = round(mobile_score, 1)
        row["desktop_score"] = round(desktop_score, 1)
        
        summary.append(row)
    
    return summary, head_to_head


def print_detailed_stats(head_to_head, model_list):
    """打印详细的 head-to-head 统计"""
    print("\n" + "="*80)
    print("Detailed Head-to-Head Statistics")
    print("="*80)
    
    for model_a in model_list:
        for model_b in model_list:
            if model_a >= model_b:
                continue
            
            stats_ab = head_to_head[model_a][model_b]
            stats_ba = head_to_head[model_b][model_a]
            
            if stats_ab["total"] == 0:
                continue
            
            print(f"\n{model_a} vs {model_b}:")
            print(f"  {model_a}: {stats_ab['wins']}W / {stats_ab['losses']}L / {stats_ab['draws']}D (Total: {stats_ab['total']})")
            print(f"    Mobile: {stats_ab['mobile_wins']}W / {stats_ab['mobile_total'] - stats_ab['mobile_wins']}L")
            print(f"    Desktop: {stats_ab['desktop_wins']}W / {stats_ab['desktop_total'] - stats_ab['desktop_wins']}L")


def extract_prefix_from_results_file(results_file):
    """从结果文件名中提取前缀 (如: question_sample_10_v2_20260527_171157)"""
    basename = os.path.basename(results_file)
    # 去掉 _pairwise_results.json 后缀
    if basename.endswith("_pairwise_results.json"):
        return basename[:-len("_pairwise_results.json")]
    # 如果就是 pairwise_results.json (无时间戳的老格式)
    if basename == "pairwise_results.json":
        return "question_sample_10_v2"
    # 默认使用文件stem
    return os.path.splitext(basename)[0]


def main():
    # 先加载配置获取默认值
    from util.config_loader import config
    default_data_file = config.get("benchmark.data_file", "Questions/question_sample_10_v1.jsonl")

    parser = argparse.ArgumentParser(description="Analyze pairwise evaluation results")
    parser.add_argument("--results-file", default=None, help="Path to pairwise_results.json")
    parser.add_argument("--questions-file", default=default_data_file, help="Path to questions JSONL file")
    parser.add_argument("--output-file", default=None, help="Output path for model_rankings.jsonl (auto-generated if not provided)")
    args = parser.parse_args()

    # 从配置文件读取模型列表
    model_list = config.get("benchmark.model_list", [])

    if not model_list:
        print("Error: No model list found in config")
        return
    
    # 规范化模型名称（将 . 替换为 -）
    model_list_normalized = [normalize_model_name(m) for m in model_list]
    print(f"Normalized model names: {model_list_normalized}")

    # 自动发现最新的结果文件
    if args.results_file is None:
        eval_dir = "arena-bench-result/pairwise_eval"
        result_files = [f for f in os.listdir(eval_dir) if f.endswith("_pairwise_results.json")]
        if not result_files:
            print(f"Error: No *_pairwise_results.json files found in {eval_dir}")
            return
        # 按修改时间排序，取最新的
        result_files.sort(key=lambda f: os.path.getmtime(os.path.join(eval_dir, f)), reverse=True)
        args.results_file = os.path.join(eval_dir, result_files[0])
        print(f"Auto-selected results file: {args.results_file}")

    # 生成输出文件路径
    if args.output_file is None:
        file_prefix = extract_prefix_from_results_file(args.results_file)
        args.output_file = f"arena-bench-result/pairwise_eval/{file_prefix}_model_rankings.jsonl"

    print(f"Model list: {model_list}")
    print(f"Loading results from: {args.results_file}")
    print(f"Loading questions from: {args.questions_file}")

    # 加载数据
    questions = load_questions(args.questions_file)
    results = load_results(args.results_file)

    print(f"Loaded {len(questions)} questions and {len(results)} results")

    # 分析结果
    summary, head_to_head = analyze_results(results, questions, model_list, model_list_normalized)

    # 打印详细统计
    print_detailed_stats(head_to_head, model_list_normalized)

    # 保存结果
    print(f"\n{'='*80}")
    print("Model Rankings Summary")
    print("="*80)

    # 按总分排序
    summary_sorted = sorted(summary, key=lambda x: x["total_score"], reverse=True)

    for row in summary_sorted:
        print(f"\nModel: {row['model']}")
        print(f"  Total Score: {row['total_score']}")
        print(f"  Mobile Score: {row['mobile_score']}")
        print(f"  Desktop Score: {row['desktop_score']}")
        vs_results = {k: v for k, v in row.items() if k not in ['model', 'total_score', 'mobile_score', 'desktop_score']}
        print(f"  VS Results: {vs_results}")

    # 保存为 jsonl
    with open(args.output_file, "w", encoding="utf-8") as f:
        for row in summary_sorted:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\n{'='*80}")
    print(f"Results saved to: {args.output_file}")
    print("="*80)


if __name__ == "__main__":
    main()
