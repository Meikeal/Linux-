#!/usr/bin/env python3
# =============================================================================
# report.py - 巡检报告生成模块
# 将系统状态、日志摘要和诊断建议汇总为 Markdown/HTML 报告
# =============================================================================

import sys
import os
import argparse
import re
from datetime import datetime
from html import escape

VERSION = "1.0.0"


def generate_markdown(check_result: str, log_result: str, diagnose_result: str) -> str:
    """生成 Markdown 格式报告"""
    lines = []
    lines.append("# Linux 运维智能巡检报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**主机名**: {os.uname().nodename if hasattr(os, 'uname') else 'N/A'}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 目录
    lines.append("## 目录")
    lines.append("")
    lines.append("1. [系统状态巡检](#系统状态巡检)")
    lines.append("2. [日志异常分析](#日志异常分析)")
    lines.append("3. [诊断建议](#诊断建议)")
    lines.append("4. [汇总信息](#汇总信息)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. 系统状态
    lines.append("## 系统状态巡检")
    lines.append("")
    if check_result:
        # 提取预警摘要
        warns = re.findall(r'\[WARN\] (.*)', check_result)
        errors = re.findall(r'\[ERROR\] (.*)', check_result)
        if warns or errors:
            lines.append("### 异常摘要")
            lines.append("")
            if errors:
                lines.append(f"**严重问题 ({len(errors)} 项):**")
                for e in errors:
                    lines.append(f"- ❌ {e}")
                lines.append("")
            if warns:
                lines.append(f"**警告 ({len(warns)} 项):**")
                for w in warns:
                    lines.append(f"- ⚠️ {w}")
                lines.append("")

        lines.append("### 巡检详情")
        lines.append("")
        lines.append("```")
        lines.append(check_result.strip())
        lines.append("```")
    else:
        lines.append("_（无系统巡检数据）_")
    lines.append("")

    # 2. 日志分析
    lines.append("## 日志异常分析")
    lines.append("")
    if log_result:
        # 提取关键信息
        total_match = re.search(r'总行数:\s*(\d+)', log_result)
        anomaly_match = re.search(r'异常事件:\s*(\d+)', log_result)
        lines.append("### 分析摘要")
        lines.append("")
        if total_match:
            lines.append(f"- 分析日志行数: {total_match.group(1)}")
        if anomaly_match:
            lines.append(f"- 异常事件数: {anomaly_match.group(1)}")
        lines.append("")

        lines.append("### 分析详情")
        lines.append("")
        lines.append("```")
        lines.append(log_result.strip())
        lines.append("```")
    else:
        lines.append("_（无日志分析数据）_")
    lines.append("")

    # 3. 诊断建议
    lines.append("## 诊断建议")
    lines.append("")
    if diagnose_result:
        lines.append(diagnose_result.strip())
    else:
        lines.append("_（无诊断建议数据）_")
    lines.append("")

    # 4. 汇总
    lines.append("---")
    lines.append("")
    lines.append("## 汇总信息")
    lines.append("")
    lines.append("| 项目 | 状态 |")
    lines.append("|------|------|")
    if check_result:
        lines.append(f"| 系统巡检 | ✅ 已完成 |")
    else:
        lines.append(f"| 系统巡检 | ❌ 未执行 |")
    if log_result:
        lines.append(f"| 日志分析 | ✅ 已完成 |")
    else:
        lines.append(f"| 日志分析 | ❌ 未执行 |")
    if diagnose_result:
        lines.append(f"| 诊断建议 | ✅ 已生成 |")
    else:
        lines.append(f"| 诊断建议 | ❌ 未生成 |")
    lines.append("")

    lines.append(f"_报告由 ops-assist v{VERSION} 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")

    return "\n".join(lines)


def generate_html(check_result: str, log_result: str, diagnose_result: str) -> str:
    """生成 HTML 格式报告"""
    # 先转Markdown为HTML的简单实现
    md_content = generate_markdown(check_result, log_result, diagnose_result)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Linux 运维智能巡检报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .report-container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #2c3e50; margin-top: 30px; }}
        h3 {{ color: #555; }}
        pre {{ background: #f8f8f8; border: 1px solid #ddd; padding: 15px; overflow-x: auto; font-size: 13px; border-radius: 4px; }}
        .warn {{ color: #e67e22; }}
        .error {{ color: #e74c3c; }}
        .ok {{ color: #27ae60; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #f8f8f8; }}
        hr {{ border: none; border-top: 1px solid #eee; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="report-container">
        <pre style="background:none;border:none;padding:0;font-family:inherit;font-size:inherit;white-space:pre-wrap;">
{escape(md_content)}
        </pre>
    </div>
    <p style="text-align:center;color:#999;margin-top:20px;font-size:12px;">
        Generated by ops-assist v{VERSION} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</body>
</html>"""

    return html


def main():
    parser = argparse.ArgumentParser(
        description="Linux 运维智能巡检 - 报告生成模块"
    )
    parser.add_argument(
        "--input", "-i",
        nargs=3,
        metavar=("CHECK_LOG", "ANALYZE_LOG", "DIAGNOSE_LOG"),
        help="依次指定: 系统巡检结果 日志分析结果 诊断建议结果",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="报告输出路径",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "html"],
        default="markdown",
        help="报告格式 (默认: markdown)",
    )

    args = parser.parse_args()

    check_result = ""
    log_result = ""
    diagnose_result = ""

    if args.input:
        files = args.input
        for i, filepath in enumerate(files):
            if filepath and os.path.isfile(filepath):
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if i == 0:
                    check_result = content
                elif i == 1:
                    log_result = content
                elif i == 2:
                    diagnose_result = content
    else:
        # 尝试从 stdin 读取（支持管道输入）
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            # 尝试按分隔符拆分
            sections = raw.split("\n---\n")
            if len(sections) >= 1:
                check_result = sections[0]
            if len(sections) >= 2:
                log_result = sections[1]
            if len(sections) >= 3:
                diagnose_result = sections[2]

    # 生成报告
    if args.format == "html":
        report = generate_html(check_result, log_result, diagnose_result)
    else:
        report = generate_markdown(check_result, log_result, diagnose_result)

    # 输出
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
