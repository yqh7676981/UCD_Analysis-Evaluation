#!/usr/bin/env python3
"""
详细分析 pairwise_results.json，生成每对模型之间的详细比较数据
输出包含15组模型对，每组10个问题的详细评分和可视化数据
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from itertools import combinations


def normalize_model_name(name):
    """将模型名称中的 . 替换为 -"""
    return name.replace(".", "-") if name else name


def load_questions(data_file):
    """加载问题列表，获取每个问题的 class (Mobile/Desktop)"""
    questions = {}
    with open(data_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                q = json.loads(line)
                qid = q.get("ID") or q.get("id")
                questions[qid] = {
                    "class": q.get("class", "Mobile"),
                    "category": q.get("类别", ""),
                    "subcategory": q.get("子场景", ""),
                    "task": q.get("任务名称", ""),
                    "question": q.get("question", "")
                }
    return questions


def load_results(results_file):
    """加载评估结果"""
    with open(results_file, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_pairwise_detail(results, questions, model_list):
    """
    详细分析每对模型之间的比较
    返回15组数据，每组包含10个问题的详细比较
    """
    # 规范化模型名称
    model_list_norm = [normalize_model_name(m) for m in model_list]
    model_name_map = {orig: norm for orig, norm in zip(model_list, model_list_norm)}
    
    # 初始化数据结构
    # {pair_key: {questions: [], summary: {}}}
    pairs_data = {}
    
    # 生成所有模型对
    for i, model_a in enumerate(model_list_norm):
        for model_b in model_list_norm[i+1:]:
            pair_key = f"{model_a}_vs_{model_b}"
            pairs_data[pair_key] = {
                "model_a": model_a,
                "model_b": model_b,
                "questions": [],
                "summary": {
                    "total": 0,
                    "model_a_wins": 0,
                    "model_b_wins": 0,
                    "draws": 0,
                    "mobile_total": 0,
                    "mobile_a_wins": 0,
                    "mobile_b_wins": 0,
                    "desktop_total": 0,
                    "desktop_a_wins": 0,
                    "desktop_b_wins": 0
                },
                "dimensions_avg": {
                    "color_harmony": {"model_a": 0, "model_b": 0, "count": 0},
                    "layout_structure": {"model_a": 0, "model_b": 0, "count": 0},
                    "style_consistency": {"model_a": 0, "model_b": 0, "count": 0},
                    "scene_fit": {"model_a": 0, "model_b": 0, "count": 0}
                }
            }
    
    # 处理每条结果
    for result in results:
        if result.get("status") != "success":
            continue
        
        model_a_orig = result["model_a"]
        model_b_orig = result["model_b"]
        model_a = model_name_map.get(model_a_orig, normalize_model_name(model_a_orig))
        model_b = model_name_map.get(model_b_orig, normalize_model_name(model_b_orig))
        
        qid = result["id"]
        winner = result.get("winner", "")
        dimensions = result.get("dimensions", {})

        # 优先从 result 中获取 class，如果不存在则从 questions 文件加载
        qinfo_base = questions.get(qid, {"class": "Mobile", "category": "", "subcategory": "", "task": "", "question": ""})
        qclass_from_result = result.get("class")
        qinfo = {
            "class": qclass_from_result or qinfo_base["class"],
            "category": qinfo_base["category"],
            "subcategory": qinfo_base["subcategory"],
            "task": qinfo_base["task"],
            "question": qinfo_base["question"]
        }
        
        # 确定pair_key（保持字母顺序）
        if model_a < model_b:
            pair_key = f"{model_a}_vs_{model_b}"
            a_is_first = True
        else:
            pair_key = f"{model_b}_vs_{model_a}"
            a_is_first = False
        
        if pair_key not in pairs_data:
            continue
        
        # 处理胜负统计
        pair = pairs_data[pair_key]
        pair["summary"]["total"] += 1
        
        # 判断胜负（考虑顺序）
        if winner == "A":
            if a_is_first:
                pair["summary"]["model_a_wins"] += 1
            else:
                pair["summary"]["model_b_wins"] += 1
        elif winner == "B":
            if a_is_first:
                pair["summary"]["model_b_wins"] += 1
            else:
                pair["summary"]["model_a_wins"] += 1
        else:
            pair["summary"]["draws"] += 1
        
        # 按设备类型统计
        if qinfo["class"] == "Mobile":
            pair["summary"]["mobile_total"] += 1
            if winner == "A":
                if a_is_first:
                    pair["summary"]["mobile_a_wins"] += 1
                else:
                    pair["summary"]["mobile_b_wins"] += 1
            elif winner == "B":
                if a_is_first:
                    pair["summary"]["mobile_b_wins"] += 1
                else:
                    pair["summary"]["mobile_a_wins"] += 1
        else:
            pair["summary"]["desktop_total"] += 1
            if winner == "A":
                if a_is_first:
                    pair["summary"]["desktop_a_wins"] += 1
                else:
                    pair["summary"]["desktop_b_wins"] += 1
            elif winner == "B":
                if a_is_first:
                    pair["summary"]["desktop_b_wins"] += 1
                else:
                    pair["summary"]["desktop_a_wins"] += 1
        
        # 处理维度评分
        dim_scores = {}
        for dim_name, dim_data in dimensions.items():
            if dim_name in pair["dimensions_avg"]:
                score_a = dim_data.get("score_a", 0)
                score_b = dim_data.get("score_b", 0)
                pair["dimensions_avg"][dim_name]["model_a"] += score_a
                pair["dimensions_avg"][dim_name]["model_b"] += score_b
                pair["dimensions_avg"][dim_name]["count"] += 1
                
                dim_scores[dim_name] = {
                    "better": dim_data.get("better", ""),
                    "score_a": score_a if a_is_first else score_b,
                    "score_b": score_b if a_is_first else score_a,
                    "reason": dim_data.get("reason", "")
                }
        
        # 添加问题详情
        question_detail = {
            "id": qid,
            "class": qinfo["class"],
            "category": qinfo["category"],
            "subcategory": qinfo["subcategory"],
            "task": qinfo["task"],
            "question": qinfo["question"],
            "winner": "A" if (winner == "A" and a_is_first) or (winner == "B" and not a_is_first) else ("B" if (winner == "B" and a_is_first) or (winner == "A" and not a_is_first) else "draw"),
            "rationale": result.get("rationale", ""),
            "dimensions": dim_scores,
            "key_differences": result.get("key_differences", [])
        }
        pair["questions"].append(question_detail)
    
    # 计算平均值和最终统计
    for pair_key, pair in pairs_data.items():
        # 计算各维度平均分
        for dim_name, dim_data in pair["dimensions_avg"].items():
            count = dim_data["count"]
            if count > 0:
                dim_data["model_a_avg"] = round(dim_data["model_a"] / count, 2)
                dim_data["model_b_avg"] = round(dim_data["model_b"] / count, 2)
        
        # 确定总体胜负
        a_wins = pair["summary"]["model_a_wins"]
        b_wins = pair["summary"]["model_b_wins"]
        if a_wins > b_wins:
            pair["summary"]["overall_winner"] = pair["model_a"]
        elif b_wins > a_wins:
            pair["summary"]["overall_winner"] = pair["model_b"]
        else:
            pair["summary"]["overall_winner"] = "draw"
    
    return pairs_data, model_list_norm


def save_detailed_analysis(pairs_data, output_file):
    """保存详细分析结果为 JSONL 格式"""
    with open(output_file, "w", encoding="utf-8") as f:
        for pair_key, pair_data in pairs_data.items():
            f.write(json.dumps({"pair_key": pair_key, **pair_data}, ensure_ascii=False) + "\n")
    print(f"Detailed analysis saved to: {output_file}")


def merge_win_rates_to_rankings(rankings_file, win_rates_dict):
    """
    将胜率数据合并到 model_rankings.jsonl 文件中
    为每个模型添加：wins, losses, draws, total_comparisons, win_rate
    """
    updated_lines = []
    
    with open(rankings_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            model_data = json.loads(line)
            model_name = model_data.get("model")
            
            if model_name and model_name in win_rates_dict:
                stats = win_rates_dict[model_name]
                # 添加胜率相关字段
                model_data["wins"] = stats["wins"]
                model_data["losses"] = stats["losses"]
                model_data["draws"] = stats["draws"]
                model_data["total_comparisons"] = stats["total_comparisons"]
                model_data["win_rate"] = stats["win_rate"]
            
            updated_lines.append(json.dumps(model_data, ensure_ascii=False))
    
    # 写回文件
    with open(rankings_file, "w", encoding="utf-8") as f:
        for line in updated_lines:
            f.write(line + "\n")


def calculate_model_win_rates(pairs_data, model_list):
    """
    计算每个模型的整体胜率
    对于N个模型和M个问题，每个模型要比较 (N-1)*M 次
    """
    # 统计每个模型的胜负情况
    model_stats = {}
    for model in model_list:
        model_stats[model] = {
            "total_comparisons": 0,  # 总比较次数
            "wins": 0,               # 胜利次数
            "losses": 0,           # 失败次数
            "draws": 0,            # 平局次数
            "win_rate": 0.0        # 胜率
        }
    
    # 遍历所有模型对，统计每个模型的胜负
    for pair_key, pair in pairs_data.items():
        model_a = pair["model_a"]
        model_b = pair["model_b"]
        summary = pair["summary"]
        
        # model_a 的统计
        model_stats[model_a]["total_comparisons"] += summary["total"]
        model_stats[model_a]["wins"] += summary["model_a_wins"]
        model_stats[model_a]["losses"] += summary["model_b_wins"]
        model_stats[model_a]["draws"] += summary["draws"]
        
        # model_b 的统计
        model_stats[model_b]["total_comparisons"] += summary["total"]
        model_stats[model_b]["wins"] += summary["model_b_wins"]
        model_stats[model_b]["losses"] += summary["model_a_wins"]
        model_stats[model_b]["draws"] += summary["draws"]
    
    # 计算胜率（排除平局，胜率 = 胜利次数 / (总次数 - 平局次数) * 100）
    # 或者按用户要求：胜率 = 胜利次数 / 总次数 * 100
    for model, stats in model_stats.items():
        if stats["total_comparisons"] > 0:
            # 按用户定义：胜率 = 胜利次数 / 总比较次数 * 100
            stats["win_rate"] = round(stats["wins"] / stats["total_comparisons"] * 100, 2)
            # 同时计算一个排除平局的胜率
            decisive_matches = stats["total_comparisons"] - stats["draws"]
            if decisive_matches > 0:
                stats["win_rate_no_draws"] = round(stats["wins"] / decisive_matches * 100, 2)
            else:
                stats["win_rate_no_draws"] = 0.0
    
    # 按胜率排序
    sorted_models = sorted(model_stats.items(), key=lambda x: x[1]["win_rate"], reverse=True)
    
    return sorted_models


def main():
    import argparse
    # 先加载配置获取默认值
    from util.config_loader import config
    default_data_file = config.get("benchmark.data_file", "Questions/question_sample_10_v1.jsonl")

    parser = argparse.ArgumentParser(description="Detailed pairwise evaluation analysis")
    parser.add_argument("--results-file", default=None, help="Path to pairwise_results.json")
    parser.add_argument("--questions-file", default=default_data_file, help="Path to questions JSONL")
    parser.add_argument("--output", default=None, help="Output JSONL file for detailed analysis")
    args = parser.parse_args()

    # 从配置文件读取模型列表
    model_list = config.get("benchmark.model_list", [])
    
    if not model_list:
        print("Error: No model list found in config")
        return

    # 自动发现最新的结果文件
    if args.results_file is None:
        eval_dir = "arena-bench-result/pairwise_eval"
        result_files = [f for f in os.listdir(eval_dir) if f.endswith("_pairwise_results.json")]
        if not result_files:
            print(f"Error: No results files found in {eval_dir}")
            return
        result_files.sort(key=lambda f: os.path.getmtime(os.path.join(eval_dir, f)), reverse=True)
        args.results_file = os.path.join(eval_dir, result_files[0])

    # 生成输出文件路径
    if args.output is None:
        prefix = os.path.basename(args.results_file).replace("_pairwise_results.json", "")
        args.output = f"arena-bench-result/pairwise_eval/{prefix}_detailed_analysis.jsonl"

    print(f"Results file: {args.results_file}")
    print(f"Questions file: {args.questions_file}")
    print(f"Models: {len(model_list)}")

    # 加载数据
    questions = load_questions(args.questions_file)
    results = load_results(args.results_file)

    print(f"Loaded {len(questions)} questions and {len(results)} results")

    # 分析数据
    pairs_data, model_list_norm = analyze_pairwise_detail(results, questions, model_list)

    print(f"Generated {len(pairs_data)} pair analyses")

    # 保存详细数据为 JSONL 格式（每行一个模型对）
    save_detailed_analysis(pairs_data, args.output)

    # 打印统计摘要
    print("\n" + "="*60)
    print("PAIRWISE ANALYSIS SUMMARY")
    print("="*60)
    for pair_key, pair in sorted(pairs_data.items()):
        summary = pair["summary"]
        winner = summary["overall_winner"]
        winner_str = "Draw" if winner == "draw" else winner
        print(f"\n{pair['model_a']} vs {pair['model_b']}:")
        print(f"  Total: {summary['total']} | A Wins: {summary['model_a_wins']} | B Wins: {summary['model_b_wins']} | Draws: {summary['draws']}")
        print(f"  Overall Winner: {winner_str}")
        print(f"  Mobile: A {summary['mobile_a_wins']} - B {summary['mobile_b_wins']}")
        print(f"  Desktop: A {summary['desktop_a_wins']} - B {summary['desktop_b_wins']}")
    
    # 计算并打印整体胜率排名
    print("\n" + "="*60)
    print("OVERALL MODEL WIN RATES (胜率排名)")
    print("="*60)
    print(f"{'Rank':<6} {'Model':<30} {'Wins':<8} {'Total':<8} {'Win Rate':<12} {'(No Draws)':<12}")
    print("-"*60)
    
    sorted_win_rates = calculate_model_win_rates(pairs_data, model_list_norm)
    win_rates_dict = {model: stats for model, stats in sorted_win_rates}
    
    for rank, (model, stats) in enumerate(sorted_win_rates, 1):
        win_rate = f"{stats['win_rate']:.1f}%"
        win_rate_no_draws = f"{stats['win_rate_no_draws']:.1f}%"
        print(f"{rank:<6} {model:<30} {stats['wins']:<8} {stats['total_comparisons']:<8} {win_rate:<12} {win_rate_no_draws:<12}")
    
    # 将胜率数据合并到 model_rankings.jsonl
    rankings_file = args.results_file.replace("_pairwise_results.json", "_model_rankings.jsonl")
    if os.path.exists(rankings_file):
        merge_win_rates_to_rankings(rankings_file, win_rates_dict)
        print(f"\nWin rates merged into: {rankings_file}")
    else:
        print(f"\nWarning: Rankings file not found: {rankings_file}")


if __name__ == "__main__":
    main()
