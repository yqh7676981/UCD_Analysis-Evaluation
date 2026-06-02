import sys
import os
from pathlib import Path
import subprocess

# 切换到项目根目录，并设置 PYTHONPATH
project_root = Path(__file__).parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))
os.environ["PYTHONPATH"] = str(project_root) + os.pathsep + os.environ.get("PYTHONPATH", "")

def run(script_path):
    """运行指定脚本，自动使用正确的 Python 解释器"""
    subprocess.run([sys.executable, script_path])

def run_analyze_pairwise_detail():
    run("./pipeline/pairwise/analyze_pairwise_detail.py")
def run_analyze_results():
    run("./pipeline/pairwise/analyze_results.py")
def run_generate_html():
    run("./pipeline/pairwise/generate_html.py")
def run_all():
    run_pairwise_evaluation()
    run_analyze_results()
    run_analyze_pairwise_detail()
    run_generate_html()
if __name__ == "__main__":
    run_all()