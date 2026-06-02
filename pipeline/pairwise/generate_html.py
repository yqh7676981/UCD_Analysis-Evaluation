#!/usr/bin/env python3
"""
从 detailed_analysis.jsonl 和 model_rankings.jsonl 生成 HTML 可视化
"""

import json
import os
import argparse
from pathlib import Path


def generate_html_visualization(pairs_data, model_list, rankings_data, output_file):
    """生成 HTML 可视化文件"""

    # 准备数据供 JavaScript 使用
    pairs_json = json.dumps(pairs_data, ensure_ascii=False)
    rankings_json = json.dumps(rankings_data, ensure_ascii=False)
    model_list_json = json.dumps(model_list, ensure_ascii=False)

    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pairwise Evaluation Visualization</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .model-card {{ transition: all 0.3s ease; }}
        .model-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1); }}
        .pair-button {{ transition: all 0.2s; }}
        .pair-button.active {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
        .dimension-bar {{ transition: width 0.5s ease; }}
        .question-card {{ cursor: pointer; transition: all 0.2s; }}
        .question-card:hover {{ background-color: #f3f4f6; }}
        .question-card.expanded {{ background-color: #eef2ff; border-color: #6366f1; }}
        .tab-button {{ transition: all 0.2s; }}
        .tab-button.active {{ border-bottom: 3px solid #6366f1; color: #6366f1; }}
        .filter-tag {{ transition: all 0.2s; }}
        .filter-tag:hover {{ transform: translateY(-1px); }}
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-7xl">
        <!-- Header -->
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">Pairwise Model Evaluation Dashboard</h1>
            <p class="text-gray-600">Detailed comparison analysis of {len(model_list)} models across {len(pairs_data)} pairs</p>
        </header>

        <!-- Tab Navigation -->
        <div class="flex border-b border-gray-200 mb-6">
            <button id="tab-overview" class="tab-button active px-6 py-3 font-medium" onclick="switchTab('overview')">
                Model Rankings
            </button>
            <button id="tab-pairs" class="tab-button px-6 py-3 font-medium text-gray-500" onclick="switchTab('pairs')">
                Pairwise Analysis
            </button>
        </div>

        <!-- Overview Tab -->
        <div id="view-overview" class="tab-content">
            <div class="bg-white rounded-xl shadow-sm p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Overall Rankings</h2>
                <div id="rankings-table" class="overflow-x-auto"></div>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <div class="bg-white rounded-xl shadow-sm p-6">
                    <h2 class="text-xl font-semibold mb-4">Score Distribution</h2>
                    <canvas id="rankings-chart" height="100"></canvas>
                </div>
                <div class="bg-white rounded-xl shadow-sm p-6">
                    <h2 class="text-xl font-semibold mb-4">Win Rate (%)</h2>
                    <canvas id="winrate-chart" height="100"></canvas>
                </div>
            </div>
        </div>

        <!-- Pairs Analysis Tab -->
        <div id="view-pairs" class="tab-content hidden">
            <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
                <!-- Sidebar: Pair Selection -->
                <div class="lg:col-span-1">
                    <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
                        <h3 class="font-semibold mb-3">Filter by Model</h3>
                        <div id="model-filter" class="flex flex-wrap gap-2">
                            <!-- Model filter tags will be inserted here -->
                        </div>
                    </div>
                    <div class="bg-white rounded-xl shadow-sm p-4">
                        <h3 class="font-semibold mb-4">Select Pair</h3>
                        <div id="pair-list" class="space-y-2 max-h-[60vh] overflow-y-auto">
                            <!-- Pair buttons will be inserted here -->
                        </div>
                    </div>
                </div>

                <!-- Main Content -->
                <div class="lg:col-span-3">
                    <div id="pair-detail" class="bg-white rounded-xl shadow-sm p-6">
                        <div class="text-center text-gray-500 py-12">
                            Select a pair to view detailed analysis
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const pairsData = {pairs_json};
        const rankingsData = {rankings_json};
        const modelList = {model_list_json};

        let currentTab = 'overview';
        let currentPair = null;
        let currentFilterModel = null;

        function switchTab(tab) {{
            currentTab = tab;
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.getElementById(`view-${{tab}}`).classList.remove('hidden');
            document.querySelectorAll('.tab-button').forEach(el => el.classList.remove('active', 'text-indigo-600'));
            document.getElementById(`tab-${{tab}}`).classList.add('active', 'text-indigo-600');

            if (tab === 'overview') {{
                renderRankings();
            }} else if (tab === 'pairs') {{
                renderModelFilter();
                renderPairList();
                if (currentPair) {{
                    renderPairDetail(currentPair);
                }}
            }}
        }}

        function renderModelFilter() {{
            const container = document.getElementById('model-filter');
            let html = '';

            // "All" button
            html += `<button class="filter-tag px-3 py-1.5 text-sm rounded-full border transition-all ${{!currentFilterModel ? 'bg-indigo-500 text-white border-indigo-500' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}}" onclick="filterByModel(null)">All</button>`;

            // Model buttons
            modelList.forEach(model => {{
                const isActive = currentFilterModel === model;
                html += `<button class="filter-tag px-3 py-1.5 text-sm rounded-full border transition-all ${{isActive ? 'bg-indigo-500 text-white border-indigo-500' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}}" onclick="filterByModel('${{model}}')">${{model}}</button>`;
            }});

            container.innerHTML = html;
        }}

        function filterByModel(model) {{
            currentFilterModel = model;
            renderModelFilter();
            renderPairList();
        }}

        function renderRankings() {{
            // Sort by total score
            const sorted = [...rankingsData].sort((a, b) => b.total_score - a.total_score);

            let html = '<table class="w-full"><thead><tr class="border-b">';
            html += '<th class="text-left py-3 px-2">Rank</th>';
            html += '<th class="text-left py-3 px-2">Model</th>';
            html += '<th class="text-center py-3 px-2">Total Score</th>';
            html += '<th class="text-center py-3 px-2">Mobile Score</th>';
            html += '<th class="text-center py-3 px-2">Desktop Score</th>';
            html += '<th class="text-center py-3 px-2 bg-indigo-50">Wins</th>';
            html += '<th class="text-center py-3 px-2 bg-indigo-50">Total</th>';
            html += '<th class="text-center py-3 px-2 bg-indigo-50">Win Rate</th>';

            // Add columns for each model
            modelList.forEach(m => {{
                html += `<th class="text-center py-3 px-2 text-xs" title="${{m}}">${{m.substring(0, 8)}}...</th>`;
            }});
            html += '</tr></thead><tbody>';

            sorted.forEach((row, idx) => {{
                const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : '';
                const winRate = row.win_rate !== undefined ? row.win_rate : 0;
                const winRateClass = winRate >= 70 ? 'text-green-600 font-bold' : winRate >= 50 ? 'text-indigo-600' : 'text-red-600';
                html += `<tr class="border-b hover:bg-gray-50">`;
                html += `<td class="py-3 px-2 font-bold">${{idx + 1}} ${{medal}}</td>`;
                html += `<td class="py-3 px-2 font-medium">${{row.model}}</td>`;
                html += `<td class="text-center py-3 px-2"><span class="bg-indigo-100 text-indigo-800 px-2 py-1 rounded-full font-bold">${{row.total_score}}</span></td>`;
                html += `<td class="text-center py-3 px-2">${{row.mobile_score}}</td>`;
                html += `<td class="text-center py-3 px-2">${{row.desktop_score}}</td>`;
                html += `<td class="text-center py-3 px-2 bg-indigo-50/50">${{row.wins !== undefined ? row.wins : '-'}}</td>`;
                html += `<td class="text-center py-3 px-2 bg-indigo-50/50">${{row.total_comparisons !== undefined ? row.total_comparisons : '-'}}</td>`;
                html += `<td class="text-center py-3 px-2 bg-indigo-50/50 ${{winRateClass}}">${{winRate.toFixed(1)}}%</td>`;

                modelList.forEach(m => {{
                    const val = row[m] || '-';
                    const color = val === 'W' ? 'text-green-600 font-bold' : val === 'L' ? 'text-red-600' : val === 'D' ? 'text-yellow-600' : 'text-gray-400';
                    html += `<td class="text-center py-3 px-2 ${{color}}">${{val}}</td>`;
                }});
                html += '</tr>';
            }});
            html += '</tbody></table>';

            document.getElementById('rankings-table').innerHTML = html;

            // Render score distribution chart
            const ctx = document.getElementById('rankings-chart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: sorted.map(r => r.model.substring(0, 15)),
                    datasets: [
                        {{
                            label: 'Mobile Score',
                            data: sorted.map(r => r.mobile_score),
                            backgroundColor: 'rgba(99, 102, 241, 0.6)',
                            borderColor: 'rgba(99, 102, 241, 1)',
                            borderWidth: 1
                        }},
                        {{
                            label: 'Desktop Score',
                            data: sorted.map(r => r.desktop_score),
                            backgroundColor: 'rgba(16, 185, 129, 0.6)',
                            borderColor: 'rgba(16, 185, 129, 1)',
                            borderWidth: 1
                        }},
                        {{
                            label: 'Total Score',
                            data: sorted.map(r => r.total_score),
                            backgroundColor: 'rgba(245, 158, 11, 0.6)',
                            borderColor: 'rgba(245, 158, 11, 1)',
                            borderWidth: 1
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: 7
                        }}
                    }}
                }}
            }});

            // Render win rate chart if data available
            if (sorted.some(r => r.win_rate !== undefined)) {{
                const winRateCanvas = document.getElementById('winrate-chart');
                if (winRateCanvas) {{
                    const winRateCtx = winRateCanvas.getContext('2d');
                    new Chart(winRateCtx, {{
                        type: 'bar',
                        data: {{
                            labels: sorted.map(r => r.model.substring(0, 15)),
                            datasets: [{{
                                label: 'Win Rate (%)',
                                data: sorted.map(r => r.win_rate || 0),
                                backgroundColor: sorted.map((r, i) => {{
                                    const rate = r.win_rate || 0;
                                    if (i === 0) return 'rgba(245, 158, 11, 0.8)';  // Gold
                                    if (i === 1) return 'rgba(156, 163, 175, 0.8)'; // Silver
                                    if (i === 2) return 'rgba(180, 83, 9, 0.8)';    // Bronze
                                    return 'rgba(99, 102, 241, 0.6)';
                                }}),
                                borderColor: sorted.map((r, i) => {{
                                    if (i === 0) return 'rgba(245, 158, 11, 1)';
                                    if (i === 1) return 'rgba(156, 163, 175, 1)';
                                    if (i === 2) return 'rgba(180, 83, 9, 1)';
                                    return 'rgba(99, 102, 241, 1)';
                                }}),
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    max: 100,
                                    ticks: {{
                                        callback: function(value) {{ return value + '%'; }}
                                    }}
                                }}
                            }},
                            plugins: {{
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            const model = sorted[context.dataIndex];
                                            return [
                                                `Win Rate: ${{(model.win_rate || 0).toFixed(1)}}%`,
                                                `Wins: ${{model.wins || 0}} / ${{model.total_comparisons || 0}}`,
                                                `Losses: ${{model.losses || 0}}`,
                                                `Draws: ${{model.draws || 0}}`
                                            ];
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}
            }}
        }}

        function renderPairList() {{
            const container = document.getElementById('pair-list');
            let html = '';

            Object.keys(pairsData).forEach(key => {{
                const pair = pairsData[key];

                // Apply model filter
                if (currentFilterModel && pair.model_a !== currentFilterModel && pair.model_b !== currentFilterModel) {{
                    return;
                }}

                const isActive = currentPair === key ? 'active' : '';
                const winner = pair.summary.overall_winner;
                const winnerBadge = winner === 'draw' ? '<span class="text-yellow-600 text-xs">Draw</span>' :
                                   `<span class="text-green-600 text-xs">${{winner}} Wins</span>`;

                html += `<button class="pair-button w-full text-left p-3 rounded-lg border border-gray-200 ${{isActive}}" onclick="selectPair('${{key}}')">`;
                html += `<div class="font-medium text-sm">${{pair.model_a}}</div>`;
                html += `<div class="text-xs text-gray-500 mb-1">vs</div>`;
                html += `<div class="font-medium text-sm">${{pair.model_b}}</div>`;
                html += `<div class="mt-2 flex justify-between items-center">`;
                html += `<span class="text-xs text-gray-400">${{pair.summary.total}} comparisons</span>`;
                html += winnerBadge;
                html += '</div></button>';
            }});

            container.innerHTML = html;
        }}

        function selectPair(key) {{
            currentPair = key;
            document.querySelectorAll('.pair-button').forEach(btn => btn.classList.remove('active'));
            event.target.closest('.pair-button').classList.add('active');
            renderPairDetail(key);
        }}

        function renderPairDetail(key) {{
            const pair = pairsData[key];
            const container = document.getElementById('pair-detail');

            // Calculate win rates
            const aWins = pair.summary.model_a_wins;
            const bWins = pair.summary.model_b_wins;
            const total = pair.summary.total;

            let html = `
                <div class="mb-6">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-2xl font-bold">${{pair.model_a}} <span class="text-gray-400 text-lg">vs</span> ${{pair.model_b}}</h2>
                        <div class="text-sm text-gray-500">${{total}} comparisons total</div>
                    </div>

                    <!-- Summary Cards -->
                    <div class="grid grid-cols-3 gap-4 mb-6">
                        <div class="bg-indigo-50 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-indigo-600">${{aWins}}</div>
                            <div class="text-sm text-indigo-800">${{pair.model_a.substring(0, 15)}} Wins</div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-gray-600">${{pair.summary.draws}}</div>
                            <div class="text-sm text-gray-800">Draws</div>
                        </div>
                        <div class="bg-emerald-50 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-emerald-600">${{bWins}}</div>
                            <div class="text-sm text-emerald-800">${{pair.model_b.substring(0, 15)}} Wins</div>
                        </div>
                    </div>

                    <!-- Device breakdown -->
                    <div class="grid grid-cols-2 gap-4 mb-6">
                        <div class="bg-blue-50 rounded-lg p-4">
                            <div class="font-semibold mb-2">Mobile (${{pair.summary.mobile_total}})</div>
                            <div class="text-sm">${{pair.model_a.substring(0, 10)}}: ${{pair.summary.mobile_a_wins}} wins</div>
                            <div class="text-sm">${{pair.model_b.substring(0, 10)}}: ${{pair.summary.mobile_b_wins}} wins</div>
                        </div>
                        <div class="bg-purple-50 rounded-lg p-4">
                            <div class="font-semibold mb-2">Desktop (${{pair.summary.desktop_total}})</div>
                            <div class="text-sm">${{pair.model_a.substring(0, 10)}}: ${{pair.summary.desktop_a_wins}} wins</div>
                            <div class="text-sm">${{pair.model_b.substring(0, 10)}}: ${{pair.summary.desktop_b_wins}} wins</div>
                        </div>
                    </div>

                    <!-- Dimensions Average -->
                    <div class="bg-gray-50 rounded-lg p-4 mb-6">
                        <h3 class="font-semibold mb-3">Average Dimension Scores</h3>
                        <div class="space-y-3">
                            ${{Object.entries(pair.dimensions_avg).map(([dim, data]) => {{
                                if (data.count === 0) return '';
                                const aAvg = data.model_a_avg;
                                const bAvg = data.model_b_avg;
                                const maxScore = 10;
                                const aPercent = (aAvg / maxScore) * 100;
                                const bPercent = (bAvg / maxScore) * 100;
                                return `
                                    <div>
                                        <div class="flex justify-between text-sm mb-1">
                                            <span class="font-medium">${{dim.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}}</span>
                                            <span>${{pair.model_a.substring(0, 10)}}: ${{aAvg}} vs ${{pair.model_b.substring(0, 10)}}: ${{bAvg}}</span>
                                        </div>
                                        <div class="relative h-6 bg-gray-200 rounded-full overflow-hidden">
                                            <div class="absolute left-0 top-0 h-full bg-indigo-500 rounded-full" style="width: ${{aPercent}}%"></div>
                                            <div class="absolute right-0 top-0 h-full bg-emerald-500 rounded-full" style="width: ${{bPercent}}%; opacity: 0.7;"></div>
                                        </div>
                                    </div>
                                `;
                            }}).join('')}}
                        </div>
                    </div>

                    <!-- Questions List -->
                    <div>
                        <h3 class="font-semibold mb-3">Per-Question Results</h3>
                        <div class="space-y-2">
                            ${{pair.questions.map((q, idx) => {{
                                const winnerColor = q.winner === 'A' ? 'border-l-4 border-l-indigo-500' : q.winner === 'B' ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-gray-400';
                                const winnerBadge = q.winner === 'A' ? '<span class="bg-indigo-100 text-indigo-800 px-2 py-1 rounded text-xs">A Wins</span>' : q.winner === 'B' ? '<span class="bg-emerald-100 text-emerald-800 px-2 py-1 rounded text-xs">B Wins</span>' : '<span class="bg-gray-100 text-gray-800 px-2 py-1 rounded text-xs">Draw</span>';
                                return `
                                    <div class="question-card bg-white border border-gray-200 rounded-lg p-4 ${{winnerColor}}" onclick="toggleQuestion(this, ${{idx}})">
                                        <div class="flex justify-between items-start">
                                            <div>
                                                <div class="font-medium">${{q.id}} - ${{q.task}}</div>
                                                <div class="text-sm text-gray-500">${{q.subcategory}} | ${{q.class}}</div>
                                            </div>
                                            ${{winnerBadge}}
                                        </div>
                                        <div class="question-detail hidden mt-4 pt-4 border-t border-gray-200" data-idx="${{idx}}">
                                            <div class="text-sm text-gray-600 mb-3">${{q.question}}</div>
                                            <div class="bg-gray-50 rounded p-3 mb-3 text-sm">
                                                <strong>Rationale:</strong> ${{q.rationale}}
                                            </div>
                                            ${{q.key_differences && q.key_differences.length > 0 ? `
                                                <div class="mb-3">
                                                    <strong class="text-sm">Key Differences:</strong>
                                                    <ul class="text-sm text-gray-600 mt-1 space-y-1">
                                                        ${{q.key_differences.map(d => `<li>• ${{d}}</li>`).join('')}}
                                                    </ul>
                                                </div>
                                            ` : ''}}
                                            ${{Object.entries(q.dimensions).length > 0 ? `
                                                <div class="grid grid-cols-2 gap-2 text-sm">
                                                    ${{Object.entries(q.dimensions).map(([dim, d]) => `
                                                        <div class="bg-white border rounded p-2">
                                                            <div class="font-medium text-xs text-gray-500 uppercase">${{dim.replace(/_/g, ' ')}}</div>
                                                            <div class="flex justify-between mt-1">
                                                                <span class="${{d.better === 'A' ? 'font-bold text-indigo-600' : ''}}">A: ${{d.score_a}}</span>
                                                                <span class="${{d.better === 'B' ? 'font-bold text-emerald-600' : ''}}">B: ${{d.score_b}}</span>
                                                            </div>
                                                        </div>
                                                    `).join('')}}
                                                </div>
                                            ` : ''}}
                                        </div>
                                    </div>
                                `;
                            }}).join('')}}
                        </div>
                    </div>
                </div>
            `;

            container.innerHTML = html;
        }}

        function toggleQuestion(card, idx) {{
            const detail = card.querySelector('.question-detail');
            if (detail.classList.contains('hidden')) {{
                // Close others
                document.querySelectorAll('.question-detail').forEach(d => d.classList.add('hidden'));
                document.querySelectorAll('.question-card').forEach(c => c.classList.remove('expanded'));

                detail.classList.remove('hidden');
                card.classList.add('expanded');
            }} else {{
                detail.classList.add('hidden');
                card.classList.remove('expanded');
            }}
        }}

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {{
            renderRankings();
        }});
    </script>
</body>
</html>
    '''

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"HTML visualization saved to: {output_file}")


def load_jsonl(filepath):
    """加载 JSONL 文件"""
    data = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                # detailed_analysis.jsonl 格式: {"pair_key": "...", ...}
                if "pair_key" in item:
                    key = item.pop("pair_key")
                    data[key] = item
    return data


def load_rankings(filepath):
    """加载排名数据"""
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def main():
    parser = argparse.ArgumentParser(description="Generate HTML visualization from analysis data")
    parser.add_argument("--detailed-file", default=None, help="Path to detailed_analysis.jsonl")
    parser.add_argument("--rankings-file", default=None, help="Path to model_rankings.jsonl")
    parser.add_argument("--output", default=None, help="Output HTML file path")
    args = parser.parse_args()

    # 自动发现最新的文件
    eval_dir = "arena-bench-result/pairwise_eval"

    if args.detailed_file is None:
        detailed_files = [f for f in os.listdir(eval_dir) if f.endswith("_detailed_analysis.jsonl")]
        if not detailed_files:
            print(f"Error: No detailed analysis files found in {eval_dir}")
            return
        detailed_files.sort(key=lambda f: os.path.getmtime(os.path.join(eval_dir, f)), reverse=True)
        args.detailed_file = os.path.join(eval_dir, detailed_files[0])
        print(f"Auto-selected detailed file: {args.detailed_file}")

    if args.rankings_file is None:
        rankings_files = [f for f in os.listdir(eval_dir) if f.endswith("_model_rankings.jsonl")]
        if not rankings_files:
            print(f"Error: No rankings files found in {eval_dir}")
            return
        rankings_files.sort(key=lambda f: os.path.getmtime(os.path.join(eval_dir, f)), reverse=True)
        args.rankings_file = os.path.join(eval_dir, rankings_files[0])
        print(f"Auto-selected rankings file: {args.rankings_file}")

    # 加载数据
    pairs_data = load_jsonl(args.detailed_file)
    rankings_data = load_rankings(args.rankings_file)

    # 提取模型列表
    model_set = set()
    for pair in pairs_data.values():
        model_set.add(pair["model_a"])
        model_set.add(pair["model_b"])
    model_list = sorted(model_set)

    # 生成输出文件路径
    if args.output is None:
        prefix = os.path.basename(args.detailed_file).replace("_detailed_analysis.jsonl", "")
        args.output = f"arena-bench-result/pairwise_eval/{prefix}_visualization.html"

    print(f"Detailed file: {args.detailed_file}")
    print(f"Rankings file: {args.rankings_file}")
    print(f"Models: {len(model_list)}")
    print(f"Pairs: {len(pairs_data)}")

    # 生成 HTML
    generate_html_visualization(pairs_data, model_list, rankings_data, args.output)

    print(f"\nVisualization generated: {args.output}")


if __name__ == "__main__":
    main()
