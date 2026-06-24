#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日AI日刊 - 运行入口
1. 读取环境变量
2. 生成日刊Markdown
3. Git commit + push
"""

import os
import sys
import subprocess
from datetime import datetime

# ============ 读取环境变量 ============
env_path = os.path.expanduser("~/AppData/Local/hermes/.env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                if key.strip() == "XIAOMI_API_KEY":
                    os.environ["XIAOMI_API_KEY"] = val.strip()

# ============ 运行生成 ============
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from generate import main as generate_main

def git_push():
    """Git add + commit + push"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    md_file = f"{date_str}.md"
    commit_msg = f"📅 daily journal: {date_str}"

    try:
        # Check if file exists and has changes
        result = subprocess.run(
            ["git", "status", "--porcelain", md_file],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if not result.stdout.strip():
            print(f"  [INFO] {md_file} 无变更，跳过push")
            return True

        # Git add
        subprocess.run(["git", "add", md_file, "README.md"], check=True,
                       cwd=os.path.dirname(os.path.abspath(__file__)))

        # Git commit
        subprocess.run(["git", "commit", "-m", commit_msg], check=True,
                       cwd=os.path.dirname(os.path.abspath(__file__)))

        # Git push
        subprocess.run(["git", "push", "origin", "main"], check=True,
                       cwd=os.path.dirname(os.path.abspath(__file__)))

        print(f"✅ 已推送到GitHub: {commit_msg}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [WARN] Git操作失败: {e}")
        return False


def main():
    print("=" * 50)
    print("  每日AI日刊 - 综合推送")
    print("=" * 50)
    print()

    # 1. 生成日刊
    output_file, already_existed = generate_main()

    if not os.path.exists(output_file):
        print("❌ 日刊文件未生成，退出")
        sys.exit(1)

    # 2. Git push（仅新生成的才push）
    if already_existed:
        print("今日已生成，无需push")
    else:
        print()
        print("--- 推送到GitHub ---")
        git_push()

    print()
    print("完成！")


if __name__ == "__main__":
    main()
