#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人机一致性对比工具
对比人工标注结果和模型pairwise评判结果的一致性
"""

import json
import pandas as pd
from collections import defaultdict
from pathlib import Path


def load_jsonl(filepath):
    """加载JSONL文件"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def parse_model_pair_key(pair_key):
    """解析pair_key获取两个模型名"""
    parts = pair_key.split('_vs_')
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None


def load_excel_data(filepath):
    """加载Excel标注数据"""
    df = pd.read_excel(filepath)
    return df


def build_human_preference_map(df):
    """
    构建人工偏好映射表
    返回: {task_id: {model_name: {'avg_score': score, 'annotators': [list], 'raw_scores': [list]}}}
    """
    task_model_scores = defaultdict(lambda: defaultdict(list))
    
    for _, row in df.iterrows():
        task_id = row.get('Task ID')
        model_name = row.get('UI 模型')
        score = row.get('整体得分（百分制）')
        annotator = row.get('标注员', '')
        
        if pd.isna(task_id) or pd.isna(model_name) or pd.isna(score):
            continue
            
        # 转换为字符串便于匹配
        if isinstance(task_id, (int, float)):
            task_key = str(int(task_id))
        else:
            task_key = str(task_id).strip()
        
        # 记录该task下该模型的得分
        task_model_scores[task_key][model_name].append({
            'score': score,
            'annotator': annotator
        })
    
    # 计算每个模型在每个task上的统计信息
    task_model_avg = {}
    for task_key, models in task_model_scores.items():
        task_model_avg[task_key] = {}
        for model_name, records in models.items():
            scores = [r['score'] for r in records]
            annotators = [r['annotator'] for r in records]
            task_model_avg[task_key][model_name] = {
                'avg_score': sum(scores) / len(scores),
                'min_score': min(scores),
                'max_score': max(scores),
                'annotator_count': len(scores),
                'annotators': annotators,
                'raw_scores': scores
            }
    
    return task_model_avg


def determine_human_preference(task_model_scores, model_a, model_b):
    """
    根据人工评分确定偏好
    返回: ('A'|'B'|'tie'|'unknown', score_a, score_b, diff)
    
    说明:
    - 'A': 人工评分A > B + 3分（A胜）
    - 'B': 人工评分B > A + 3分（B胜）
    - 'tie': |A-B| < 3分（差距太小视为平局）
    - 'unknown': 任一模型缺少人工评分，无法比较
    """
    info_a = task_model_scores.get(model_a)
    info_b = task_model_scores.get(model_b)

    score_a = info_a['avg_score'] if info_a else None
    score_b = info_b['avg_score'] if info_b else None

    # 如果任一模型缺少人工评分，标记为unknown，不参与比较
    if score_a is None or score_b is None:
        return 'unknown', score_a, score_b, None

    # 差距小于3分视为平局（tie）
    diff = score_a - score_b
    if abs(diff) < 3:
        pref = 'tie'  # 平局：人工认为两者差不多
    elif diff > 0:
        pref = 'A'    # A得分更高
    else:
        pref = 'B'    # B得分更高

    return pref, score_a, score_b, diff


def calculate_agreement(human_pref, model_pref):
    """
    计算一致性
    返回: 'agree', 'disagree', 'neutral', 或 'unknown'

    规则:
    - 人工 tie (差距<3分): 无论模型选什么，都算 agree (人工认为两者差不多)
    - 模型 tie: 人工有明确偏好时算 neutral (模型无法判断)
    - 其他情况: 人工和模型选择相同则 agree，不同则 disagree
    """
    if human_pref == 'unknown' or model_pref == 'unknown':
        return 'unknown'
    # 人工平局：无论模型选什么，都算一致（人工认为两者差不多）
    if human_pref == 'tie':
        return 'agree'
    # 模型平局：人工有明确偏好时算中性
    if model_pref == 'tie':
        return 'neutral'
    # 两者都有明确偏好
    if human_pref == model_pref:
        return 'agree'
    return 'disagree'


def format_score_info(info):
    """格式化分数信息，保留1位小数"""
    if info is None:
        return None
    return {
        'avg_score': round(info['avg_score'], 1),
        'min_score': round(info['min_score'], 1),
        'max_score': round(info['max_score'], 1),
        'annotator_count': info['annotator_count'],
        'annotators': info['annotators'],
        'raw_scores': [round(s, 1) for s in info['raw_scores']]
    }


def analyze_consistency(jsonl_data, excel_df):
    """
    分析人机一致性
    """
    # 构建人工评分映射
    human_scores = build_human_preference_map(excel_df)

    results = []

    for record in jsonl_data:
        pair_key = record.get('pair_key', '')
        model_a = record.get('model_a', '')
        model_b = record.get('model_b', '')
        questions = record.get('questions', [])

        for q in questions:
            question_id = q.get('id', '')
            question_text = q.get('question', '')
            winner = q.get('winner', '')
            task_name = q.get('task', '')
            category = q.get('category', '')
            subcategory = q.get('subcategory', '')

            # 直接使用question_id作为task_key (如 U001, E001等)
            task_key = question_id.strip()

            # 确定人工偏好
            human_pref = 'unknown'
            score_a = None
            score_b = None
            score_diff = None
            info_a = None
            info_b = None

            if task_key in human_scores:
                task_scores = human_scores[task_key]
                human_pref, score_a, score_b, score_diff = determine_human_preference(
                    task_scores, model_a, model_b
                )
                info_a = task_scores.get(model_a)
                info_b = task_scores.get(model_b)

            # 确定模型偏好
            model_pref = winner if winner in ['A', 'B', 'tie'] else 'unknown'

            # 计算一致性
            agreement = calculate_agreement(human_pref, model_pref)

            # 格式化分数（保留1位小数）
            score_a_formatted = round(score_a, 1) if score_a is not None else None
            score_b_formatted = round(score_b, 1) if score_b is not None else None
            score_diff_formatted = round(score_diff, 1) if score_diff is not None else None

            result = {
                'pair_key': pair_key,
                'model_a': model_a,
                'model_b': model_b,
                'question_id': question_id,
                'task_name': task_name,
                'category': category,
                'subcategory': subcategory,
                'question': question_text,
                'model_winner': model_pref,
                'human_preference': human_pref,
                'human_score_a': score_a_formatted,
                'human_score_b': score_b_formatted,
                'human_score_diff': score_diff_formatted,
                'human_info_a': format_score_info(info_a),
                'human_info_b': format_score_info(info_b),
                'agreement': agreement,
                'rationale': q.get('rationale', ''),
                'matched_task_id': task_key,
                'has_human_data': task_key in human_scores
            }
            results.append(result)

    return results


def calculate_statistics(results):
    """
    计算统计信息
    
    只统计有有效人工数据的记录（human_preference != 'unknown'）
    unknown的记录单独统计但不参与一致性比率计算
    """
    # 分开统计：有效记录 vs 未知记录
    valid_results = [r for r in results if r['human_preference'] != 'unknown']
    unknown_results = [r for r in results if r['human_preference'] == 'unknown']

    total_all = len(results)
    total_valid = len(valid_results)
    total_unknown = len(unknown_results)

    # 只统计有效记录中的一致性
    agree = sum(1 for r in valid_results if r['agreement'] == 'agree')
    disagree = sum(1 for r in valid_results if r['agreement'] == 'disagree')
    neutral = sum(1 for r in valid_results if r['agreement'] == 'neutral')

    stats = {
        'total_comparisons': total_all,
        'valid_comparisons': total_valid,
        'unknown_count': total_unknown,
        'agree_count': agree,
        'disagree_count': disagree,
        'neutral_count': neutral,
        'agreement_rate': agree / total_valid if total_valid > 0 else 0,
        'disagreement_rate': disagree / total_valid if total_valid > 0 else 0,
        'neutral_rate': neutral / total_valid if total_valid > 0 else 0
    }

    # 按模型对统计 - 只统计有效记录且 agreement 不为 unknown
    pair_stats = {}
    for r in valid_results:
        # 跳过 model_pref 为 unknown 的情况
        if r['agreement'] == 'unknown':
            continue
        pair_key = r['pair_key']
        if pair_key not in pair_stats:
            pair_stats[pair_key] = {'total': 0, 'agree': 0, 'disagree': 0, 'neutral': 0}
        pair_stats[pair_key]['total'] += 1
        pair_stats[pair_key][r['agreement']] += 1

    # 计算每个模型对的比率
    for pair_key, pstat in pair_stats.items():
        pstat['agreement_rate'] = pstat['agree'] / pstat['total'] if pstat['total'] > 0 else 0

    stats['by_pair'] = pair_stats

    # 按分类统计 - 只统计有效记录且 agreement 不为 unknown
    category_stats = {}
    for r in valid_results:
        # 跳过 model_pref 为 unknown 的情况
        if r['agreement'] == 'unknown':
            continue
        cat = r.get('category', 'unknown')
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'agree': 0, 'disagree': 0, 'neutral': 0}
        category_stats[cat]['total'] += 1
        category_stats[cat][r['agreement']] += 1

    for cat, cstat in category_stats.items():
        cstat['agreement_rate'] = cstat['agree'] / cstat['total'] if cstat['total'] > 0 else 0

    stats['by_category'] = category_stats

    return stats


def save_jsonl(data, filepath):
    """保存为JSONL格式"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def main():
    # 文件路径
    base_dir = Path('/Users/admin/Desktop/task/test-Pairwise')
    jsonl_path = base_dir / 'arena-bench-result/pairwise_eval/question_20260529_151012_detailed_analysis.jsonl'
    excel_path = base_dir / 'export-ej_1780043739514_g4l9kg_replaced_dedup.xlsx'
    
    print(f"加载JSONL文件: {jsonl_path}")
    jsonl_data = load_jsonl(jsonl_path)
    print(f"  加载了 {len(jsonl_data)} 条pairwise记录")
    
    print(f"加载Excel文件: {excel_path}")
    excel_df = load_excel_data(excel_path)
    print(f"  加载了 {len(excel_df)} 条人工标注记录")
    print(f"  列名: {list(excel_df.columns)}")
    
    print("\n分析人机一致性...")
    results = analyze_consistency(jsonl_data, excel_df)
    
    print(f"  分析了 {len(results)} 条对比结果")
    
    # 计算统计
    stats = calculate_statistics(results)
    
    print("\n=== 一致性统计 ===")
    print(f"总对比数: {stats['total_comparisons']}")
    print(f"有效对比数: {stats['valid_comparisons']}")
    print(f"一致数 (agree): {stats['agree_count']} ({stats['agreement_rate']:.2%})")
    print(f"不一致数 (disagree): {stats['disagree_count']} ({stats['disagreement_rate']:.2%})")
    print(f"中性 (tie): {stats['neutral_count']} ({stats['neutral_rate']:.2%})")
    print(f"无法匹配 (unknown): {stats['unknown_count']}")
    
    # 按模型对统计
    print("\n=== 按模型对统计 ===")
    for pair_key, pstat in sorted(stats['by_pair'].items()):
        print(f"{pair_key}: {pstat['agree']}/{pstat['total']} ({pstat['agreement_rate']:.1%})")

    # 按分类统计
    print("\n=== 按分类统计 ===")
    for cat, cstat in sorted(stats['by_category'].items()):
        print(f"{cat}: {cstat['agree']}/{cstat['total']} ({cstat['agreement_rate']:.1%})")
    
    # 添加统计信息到结果
    final_output = {
        'statistics': stats,
        'comparisons': results
    }
    
    # 保存完整结果（包含统计信息）为JSON
    output_json_path = base_dir / 'human_model_consistency_result.json'
    print(f"\n保存完整结果到: {output_json_path}")
    with open(output_json_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(final_output, ensure_ascii=False, indent=2))
    
    # 额外保存只有比较结果的JSONL
    output_jsonl_path = base_dir / 'human_model_consistency_comparisons.jsonl'
    save_jsonl(results, output_jsonl_path)
    print(f"对比详情保存到: {output_jsonl_path}")
    
    print("\n完成!")


if __name__ == '__main__':
    main()
