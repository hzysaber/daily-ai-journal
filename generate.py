#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日AI综合日刊生成器
- AI资讯（RSS抓取 + AI过滤）
- 技术笔记（MiMo生成，主题轮换）
- 代码片段（MiMo生成，实用小工具）
输出：YYYY-MM-DD.md
"""

import feedparser
import requests
import json
import os
import re
import hashlib
from datetime import datetime

# ============ 配置 ============

XIAOMI_API_KEY = os.environ.get("XIAOMI_API_KEY", "")
MIMO_BASE_URL = "https://api.xiaomimimo.com/v1/chat/completions"
MIMO_MODEL = "mimo-v2.5-pro"

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
TODAY = datetime.now()
DATE_STR = TODAY.strftime("%Y-%m-%d")
DAY_SEED = int(TODAY.strftime("%Y%m%d"))

# RSS源（国内可访问）
RSS_FEEDS = [
    ("36氪", "https://36kr.com/feed"),
    ("爱范儿", "https://www.ifanr.com/feed"),
]

# 技术笔记主题轮换
TECH_TOPICS = [
    "RAG（检索增强生成）的工程实践与优化技巧",
    "LLM Agent 架构设计：ReAct、Plan-and-Execute、Multi-Agent",
    "Prompt Engineering 高级技巧：Few-shot、CoT、Self-Consistency",
    "向量数据库选型与优化：ChromaDB、Milvus、Pinecone、Weaviate",
    "大模型微调实战：LoRA、QLoRA、全量微调的适用场景",
    "LangChain vs LangGraph：Agent框架对比与最佳实践",
    "大模型部署与推理优化：量化、KV Cache、vLLM、TGI",
    "Embedding模型选型与文本分块策略",
    "大模型应用的评估体系：RAGAS、人工评估、A/B测试",
    "Function Calling 与 Tool Use 的实现原理",
    "多模态大模型应用：视觉理解、语音交互",
    "大模型安全：Prompt注入防护、内容审核、幻觉检测",
    "企业级RAG系统设计：多租户、权限控制、增量更新",
    "知识图谱 + 大模型：GraphRAG的原理与实践",
    "AI Coding Agent：Cursor、Copilot、Claude Code的技术原理",
]

# 代码片段主题轮换
CODE_TOPICS = [
    "用Python实现一个简单的语义搜索函数（基于sentence-transformers）",
    "用Python实现一个LLM对话的流式输出工具",
    "用Python实现一个简单的文本分块器（支持递归字符分割）",
    "用Python实现一个向量数据库的相似度检索封装",
    "用Python实现一个Prompt模板引擎（支持变量替换和条件分支）",
    "用Python实现一个简单的Agent工具调用框架",
    "用Python实现一个RSS新闻聚合器",
    "用Python实现一个Markdown文档的RAG索引构建器",
    "用Python实现一个简单的重试装饰器（支持指数退避）",
    "用Python实现一个JSON Schema验证器",
    "用Python实现一个简单的token计数器",
    "用Python实现一个多模型API调用的统一封装",
    "用Python实现一个简单的对话历史管理器（支持滑动窗口）",
    "用Python实现一个文件内容的hash去重工具",
    "用Python实现一个简单的HTTP请求限流器",
]


# ============ 工具函数 ============

def call_mimo(prompt, max_tokens=2000, temperature=0.7):
    """调用MiMo API"""
    if not XIAOMI_API_KEY:
        return None, 0
    try:
        resp = requests.post(
            MIMO_BASE_URL,
            headers={
                "Authorization": f"Bearer {XIAOMI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MIMO_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens = usage.get("total_tokens", 0)
        return content, tokens
    except Exception as e:
        print(f"  [WARN] MiMo调用失败: {e}")
        return None, 0


def parse_json(text):
    """从文本中提取JSON"""
    match = re.search(r"[\[\{].*[\]\}]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return None


def stable_pick(items, n, seed=None):
    """基于日期种子稳定选取n个元素"""
    if seed is None:
        seed = DAY_SEED
    h = hashlib.md5(str(seed).encode()).hexdigest()
    idx = int(h[:8], 16) % max(len(items), 1)
    result = []
    for i in range(min(n, len(items))):
        result.append(items[(idx + i * 7) % len(items)])
    return result


def fetch_rss(feeds, max_per_feed=10, max_total=15):
    """抓取RSS新闻"""
    articles = []
    seen = set()
    for name, url in feeds:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                summary = re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:200].strip()
                pub = entry.get("published", "")[:16]
                if not title or title in seen:
                    continue
                seen.add(title)
                articles.append({
                    "source": name,
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "date": pub,
                })
        except Exception as e:
            print(f"  [WARN] {name}: {e}")
    return articles[:max_total]


def is_ai_related(title, summary=""):
    """判断是否AI相关"""
    text = (title + " " + summary).lower()
    keywords = [
        "ai", "人工智能", "大模型", "llm", "gpt", "claude", "gemini", "deepseek",
        "chatgpt", "copilot", "大语言模型", "深度学习", "机器学习", "transformer",
        "生成式", "aigc", "agi", "智能体", "agent", "rag", "向量", "embedding",
        "微调", "fine-tun", "lora", "多模态", "图像生成", "视频生成",
        "openai", "anthropic", "google ai", "meta ai", "百度", "文心", "通义",
        "智谱", "kimi", "huggingface", "pytorch", "机器人", "自动驾驶",
    ]
    return any(kw in text for kw in keywords)


# ============ 内容生成 ============

def get_news():
    """获取AI新闻"""
    print("[1/3] 抓取AI新闻...")
    articles = fetch_rss(RSS_FEEDS, max_per_feed=15, max_total=20)
    ai_articles = [a for a in articles if is_ai_related(a["title"], a.get("summary", ""))]
    if len(ai_articles) < 5:
        ai_articles = articles  # 太少则不过滤
    result = ai_articles[:10]
    print(f"      {len(result)} 条AI相关新闻")
    return result


def get_tech_note():
    """生成技术笔记"""
    print("[2/3] 生成技术笔记...")
    topic = stable_pick(TECH_TOPICS, 1)[0]
    prompt = f"""你是一位AI大模型技术博主，请写一篇关于"{topic}"的技术笔记。

要求：
- 中文撰写，Markdown格式
- 800-1200字
- 包含：核心概念、技术原理、代码示例或伪代码、实际应用场景、常见坑点
- 语言简洁专业，适合有一定基础的开发者阅读
- 不要加标题（标题会由外层添加）

直接输出Markdown正文，不要加任何前缀说明。"""
    result, tokens = call_mimo(prompt, max_tokens=3000, temperature=0.7)
    if result:
        print(f"      MiMo生成成功 ({tokens} tokens)")
        return topic, result, tokens
    print("      [WARN] 生成失败，使用占位文本")
    return topic, f"今日技术笔记生成失败，请检查 MiMo API 配置。", 0


def get_code_snippet():
    """生成代码片段"""
    print("[3/3] 生成代码片段...")
    topic = stable_pick(CODE_TOPICS, 1, seed=DAY_SEED + 100)[0]
    prompt = f"""你是一位Python技术博主，请写一个实用的代码片段："{topic}"

要求：
- Python 3.10+，代码简洁实用
- 包含完整的类型注解
- 包含docstring说明用法
- 包含一个简单的使用示例
- 代码量控制在30-80行
- 加上简短的中文说明（2-3行）

直接输出Markdown格式（说明+代码块+示例），不要加任何前缀。"""
    result, tokens = call_mimo(prompt, max_tokens=2000, temperature=0.6)
    if result:
        print(f"      MiMo生成成功 ({tokens} tokens)")
        return topic, result, tokens
    print("      [WARN] 生成失败")
    return topic, "代码片段生成失败。", 0


# ============ Markdown输出 ============

def generate_markdown(news, tech_topic, tech_content, code_topic, code_content):
    """生成完整的Markdown日刊"""
    weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_cn[TODAY.weekday()]

    lines = []
    lines.append(f"# 📅 每日AI日刊 — {DATE_STR} {weekday}")
    lines.append("")
    lines.append("> 每日综合推送：AI资讯 + 技术笔记 + 代码片段")
    lines.append("")
    lines.append("---")
    lines.append("")

    # AI资讯
    lines.append("## 🔥 AI 资讯速递")
    lines.append("")
    if news:
        for i, a in enumerate(news, 1):
            title = a["title"]
            summary = a.get("summary", "")
            link = a.get("link", "")
            source = a.get("source", "")
            if link:
                lines.append(f"**{i}. [{title}]({link})**")
            else:
                lines.append(f"**{i}. {title}**")
            if summary:
                lines.append(f"   {summary[:150]}")
            if source:
                lines.append(f"   *来源: {source}*")
            lines.append("")
    else:
        lines.append("*今日RSS源未抓取到AI相关新闻。*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # 技术笔记
    lines.append(f"## 📝 技术笔记：{tech_topic}")
    lines.append("")
    lines.append(tech_content)
    lines.append("")
    lines.append("---")
    lines.append("")

    # 代码片段
    lines.append(f"## 💻 代码片段：{code_topic}")
    lines.append("")
    lines.append(code_content)
    lines.append("")
    lines.append("---")
    lines.append("")

    # 尾部
    lines.append(f"*由 Hermes Agent 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")

    return "\n".join(lines)


# ============ 主入口 ============

def main():
    print(f"=== 每日AI日刊生成器 ===")
    print(f"日期: {DATE_STR}")
    print()

    output_file = os.path.join(OUTPUT_DIR, f"{DATE_STR}.md")

    # 检查今天是否已生成
    if os.path.exists(output_file):
        print(f"今日日刊已存在: {output_file}")
        print("跳过生成。如需重新生成，请删除该文件。")
        return output_file, True

    total_tokens = 0

    # 1. 抓取新闻
    news = get_news()

    # 2. 生成技术笔记
    tech_topic, tech_content, tech_tokens = get_tech_note()
    total_tokens += tech_tokens

    # 3. 生成代码片段
    code_topic, code_content, code_tokens = get_code_snippet()
    total_tokens += code_tokens

    # 4. 组装Markdown
    md = generate_markdown(news, tech_topic, tech_content, code_topic, code_content)

    # 5. 写入文件
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)

    print()
    print(f"✅ 日刊生成完成: {output_file}")
    print(f"   新闻: {len(news)} 条")
    print(f"   技术笔记: {tech_topic}")
    print(f"   代码片段: {code_topic}")
    print(f"   Token消耗: {total_tokens}")

    return output_file, False


if __name__ == "__main__":
    main()
