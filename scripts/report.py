#!/usr/bin/env python3
# =============================================================================
# report.py - 巡检报告生成模块
# 将系统巡检、日志分析和诊断建议汇总为 Markdown/HTML 报告
# =============================================================================

import argparse
import os
import re
import sys
from datetime import datetime
from html import escape

VERSION = "1.0.0"

CHECK_EXPLAIN = {
    "系统基本信息": (
        "采集主机名、内核版本、系统版本、运行时间和当前时间。",
        "用于确认巡检对象是否正确，也方便后续排查时定位服务器环境。",
    ),
    "CPU 状态": (
        "检查 CPU 使用率、1 分钟负载和 CPU 核心数。",
        "负载低于配置阈值表示当前计算压力正常；偏高时需要关注高占用进程。",
    ),
    "内存状态": (
        "检查总内存、已用内存、可用内存和 Swap 使用情况。",
        "内存使用率超过阈值会触发告警，说明服务可能存在内存压力或异常占用。",
    ),
    "磁盘状态": (
        "检查各分区容量使用率和 inode 使用率。",
        "磁盘或 inode 接近耗尽会影响日志写入、服务启动和文件上传。",
    ),
    "进程状态": (
        "统计进程总数，列出 CPU/内存占用最高的进程，并检查僵尸进程。",
        "用于发现资源占用异常、残留进程或服务进程异常退出后的系统表现。",
    ),
    "端口状态": (
        "检查配置文件 WATCH_PORTS 中的端口是否处于监听状态。",
        "例如本项目检查 22 端口用于 SSH，80 端口用于对外提供博客访问。",
    ),
    "服务状态": (
        "检查配置文件 WATCH_SERVICES 中的 systemd 服务是否存在并运行。",
        "服务为 active 表示 systemd 认为服务正在运行；failed/inactive 需要继续查看日志。",
    ),
    "网络状态": (
        "统计 TCP 连接中的 ESTABLISHED、LISTEN、TIME_WAIT 等状态数量。",
        "用于判断服务器是否有正常连接、监听服务，以及是否出现大量短连接堆积。",
    ),
    "Web 健康检查": (
        "访问配置文件 HEALTH_URLS 中的健康检查地址，并判断响应中是否包含 ok。",
        "本项目在服务器本机访问 http://127.0.0.1/healthz.txt，确认博客服务本地可用；外部用户访问公网 IP。",
    ),
    "巡检汇总": (
        "汇总前面所有检查项的 OK/WARN/ERROR 数量。",
        "如果没有异常，说明当前服务器、博客服务和基础资源状态良好。",
    ),
}


def normalize_status(body: str) -> str:
    if "[ERROR]" in body:
        return "ERROR"
    if "[WARN]" in body:
        return "WARN"
    if "[OK]" in body:
        return "OK"
    if "[SKIP]" in body:
        return "SKIP"
    return "INFO"


def status_text(status: str) -> str:
    mapping = {
        "OK": "正常",
        "WARN": "需要关注",
        "ERROR": "异常",
        "SKIP": "已跳过",
        "INFO": "已记录",
    }
    return mapping.get(status, status)


def escape_cell(text: str) -> str:
    return " ".join(text.replace("|", "\\|").split())


def parse_check_sections(check_result: str):
    sections = []
    current_title = None
    current_lines = []

    for line in check_result.splitlines():
        title_match = re.match(r"^\s{2}(.+?)\s*$", line)
        if line.strip("=") == "" and len(line.strip()) >= 10:
            continue
        if title_match and title_match.group(1) in CHECK_EXPLAIN:
            if current_title:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = title_match.group(1)
            current_lines = []
            continue
        if current_title:
            current_lines.append(line)

    if current_title:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return sections


def extract_key_findings(body: str, limit: int = 3) -> str:
    selected = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("="):
            continue
        if any(mark in line for mark in ("[ERROR]", "[WARN]", "[OK]", "[SKIP]")):
            selected.append(line)
        elif len(selected) < 1 and ":" in line:
            selected.append(line)
        if len(selected) >= limit:
            break
    return "；".join(selected) if selected else "该项已完成采集，未输出额外告警。"


def build_check_explanation(check_result: str) -> str:
    sections = parse_check_sections(check_result)
    if not sections:
        return ""

    lines = []
    lines.append("### 巡检项目说明")
    lines.append("")
    lines.append("| 检查项目 | 检查内容 | 当前状态 | 结果说明 |")
    lines.append("|---|---|---|---|")
    for title, body in sections:
        content, meaning = CHECK_EXPLAIN.get(title, ("记录该项运行结果。", "用于辅助定位系统状态。"))
        status = normalize_status(body)
        findings = extract_key_findings(body)
        detail = f"{status_text(status)}。{findings}。{meaning}"
        lines.append(
            f"| {escape_cell(title)} | {escape_cell(content)} | {escape_cell(status_text(status))} | {escape_cell(detail)} |"
        )
    lines.append("")
    return "\n".join(lines)


def extract_alerts(text: str):
    warns = re.findall(r"\[WARN\]\s*(.*)", text)
    errors = re.findall(r"\[ERROR\]\s*(.*)", text)
    return errors, warns


def generate_markdown(check_result: str, log_result: str, diagnose_result: str) -> str:
    lines = []
    lines.append("# Linux 运维智能巡检报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**主机名**: {os.uname().nodename if hasattr(os, 'uname') else 'N/A'}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 目录")
    lines.append("")
    lines.append("1. [系统状态巡检](#系统状态巡检)")
    lines.append("2. [日志异常分析](#日志异常分析)")
    lines.append("3. [诊断建议](#诊断建议)")
    lines.append("4. [汇总信息](#汇总信息)")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 系统状态巡检")
    lines.append("")
    if check_result:
        errors, warns = extract_alerts(check_result)
        if errors or warns:
            lines.append("### 异常摘要")
            lines.append("")
            if errors:
                lines.append(f"**严重问题 ({len(errors)} 项):**")
                for item in errors:
                    lines.append(f"- [ERROR] {item}")
                lines.append("")
            if warns:
                lines.append(f"**警告 ({len(warns)} 项):**")
                for item in warns:
                    lines.append(f"- [WARN] {item}")
                lines.append("")
        else:
            lines.append("### 异常摘要")
            lines.append("")
            lines.append("- 未发现 ERROR/WARN 级别异常。")
            lines.append("")

        explanation = build_check_explanation(check_result)
        if explanation:
            lines.append(explanation)

        lines.append("### 原始巡检输出")
        lines.append("")
        lines.append("```text")
        lines.append(check_result.strip())
        lines.append("```")
    else:
        lines.append("_（无系统巡检数据）_")
    lines.append("")

    lines.append("## 日志异常分析")
    lines.append("")
    if log_result:
        lines.append("### 分析说明")
        lines.append("")
        lines.append("日志模块会扫描系统日志中的 error、failed、denied、timeout 等关键词，并提取异常上下文。")
        lines.append("")
        lines.append("### 原始日志分析输出")
        lines.append("")
        lines.append("```text")
        lines.append(log_result.strip())
        lines.append("```")
    else:
        lines.append("_（无日志分析数据）_")
    lines.append("")

    lines.append("## 诊断建议")
    lines.append("")
    if diagnose_result:
        lines.append(diagnose_result.strip())
    else:
        lines.append("_（无诊断建议数据）_")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 汇总信息")
    lines.append("")
    lines.append("| 项目 | 状态 |")
    lines.append("|---|---|")
    lines.append(f"| 系统巡检 | {'已完成' if check_result else '未执行'} |")
    lines.append(f"| 日志分析 | {'已完成' if log_result else '未执行'} |")
    lines.append(f"| 诊断建议 | {'已生成' if diagnose_result else '未生成'} |")
    lines.append("")
    lines.append(f"_报告由 ops-assist v{VERSION} 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
    return "\n".join(lines)


def generate_html(check_result: str, log_result: str, diagnose_result: str) -> str:
    md_content = generate_markdown(check_result, log_result, diagnose_result)
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Linux 运维智能巡检报告</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      max-width: 1080px;
      margin: 40px auto;
      padding: 20px;
      background: #f5f7fb;
      color: #263238;
      line-height: 1.7;
    }}
    .report-container {{
      background: #fff;
      padding: 40px;
      border-radius: 8px;
      box-shadow: 0 8px 30px rgba(20, 35, 60, 0.08);
    }}
    pre {{
      white-space: pre-wrap;
      overflow-x: auto;
      background: #f8fafc;
      border: 1px solid #dfe7ef;
      border-radius: 6px;
      padding: 16px;
    }}
  </style>
</head>
<body>
  <div class="report-container">
    <pre>{escape(md_content)}</pre>
  </div>
</body>
</html>"""
    return html


def read_inputs(paths):
    results = ["", "", ""]
    for i, filepath in enumerate(paths or []):
        if filepath and os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                results[i] = f.read()
    return results


def main():
    parser = argparse.ArgumentParser(description="Linux 运维智能巡检 - 报告生成模块")
    parser.add_argument(
        "--input",
        "-i",
        nargs=3,
        metavar=("CHECK_LOG", "ANALYZE_LOG", "DIAGNOSE_LOG"),
        help="依次指定: 系统巡检结果、日志分析结果、诊断建议结果",
    )
    parser.add_argument("--output", "-o", default=None, help="报告输出路径")
    parser.add_argument(
        "--format",
        "-f",
        choices=["markdown", "html"],
        default="markdown",
        help="报告格式 (默认: markdown)",
    )
    args = parser.parse_args()

    if args.input:
        check_result, log_result, diagnose_result = read_inputs(args.input)
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
        parts = raw.split("\n---\n")
        check_result = parts[0] if len(parts) >= 1 else ""
        log_result = parts[1] if len(parts) >= 2 else ""
        diagnose_result = parts[2] if len(parts) >= 3 else ""
    else:
        check_result = log_result = diagnose_result = ""

    report = (
        generate_html(check_result, log_result, diagnose_result)
        if args.format == "html"
        else generate_markdown(check_result, log_result, diagnose_result)
    )

    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已保存至: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
