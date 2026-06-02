# Pairwise 模型对比评估

对比多个大语言模型在设计任务上的表现，生成胜负统计和可视化报告。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 编辑 config.yaml 配置要对比的模型
vi config.yaml

# 3. 运行pairwise评估
python run_pairwise.py
```

## 项目结构

```
├── run.py              # 主入口
├── config.yaml         # 模型配置
├── data/               # 问题数据
├── pipeline/pairwise/  # 评估流程
│   ├── analyze_results.py
│   └── generate_html.py
└── arena-bench-result/ # 输出结果
```

## 配置示例

```yaml
benchmark:
  model_list:
    - claude-opus-4-7-thinking
    - deepseek-v4-flash
    - gpt-4o
```

## 输出

- `arena-bench-result/pairwise_eval/` - 评估结果 JSON
- `html_file/` - HTML 可视化报告

## 依赖

- Python 3.8+
- OpenAI API
