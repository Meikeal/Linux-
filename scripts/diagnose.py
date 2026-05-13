#!/usr/bin/env python3
# =============================================================================
# diagnose.py - 诊断建议生成模块
# 根据巡检结果和日志特征生成初步诊断建议
# =============================================================================

import sys
import os
import argparse
import re
from datetime import datetime

# 诊断规则库
DIAGNOSIS_RULES = {
    "disk_high": {
        "pattern": r"磁盘使用率过高.*?(\d+)%",
        "suggestion": [
            "磁盘空间不足可能导致服务异常或数据丢失",
            "建议:",
            "  1. 使用 'du -sh /*' 查找占用空间大的目录",
            "  2. 清理旧日志文件: journalctl --vacuum-size=500M",
            "  3. 清理 apt/yum 缓存: apt clean / yum clean all",
            "  4. 检查 /var/log 目录大小，考虑配置 logrotate",
        ],
    },
    "mem_high": {
        "pattern": r"内存使用率过高.*?(\d+)%",
        "suggestion": [
            "内存使用率过高可能影响系统性能",
            "建议:",
            "  1. 使用 'ps aux --sort=-%mem | head -10' 查看内存占用最高的进程",
            "  2. 检查是否有内存泄漏的进程",
            "  3. 考虑增加 swap 空间作为临时缓解",
            "  4. 使用 'free -h' 持续监控内存变化",
        ],
    },
    "cpu_high": {
        "pattern": r"系统负载偏高",
        "suggestion": [
            "CPU 负载偏高，系统响应可能变慢",
            "建议:",
            "  1. 使用 'top' 或 'htop' 查看 CPU 占用最高的进程",
            "  2. 使用 'mpstat -P ALL' 查看各核心负载分布",
            "  3. 检查 crontab 是否有密集定时任务",
            "  4. 考虑调整进程优先级或限制 CPU 使用",
        ],
    },
    "ssh_failed": {
        "pattern": r"SSH.*失败.*(\d+)次",
        "suggestion": [
            "SSH 登录失败次数较多，可能存在暴力破解风险",
            "建议:",
            "  1. 查看失败来源 IP: grep 'Failed password' /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn",
            "  2. 安装 fail2ban 自动封禁恶意 IP",
            "  3. 禁用 root SSH 登录: 编辑 /etc/ssh/sshd_config 设置 PermitRootLogin no",
            "  4. 修改 SSH 默认端口 (22) 为非标准端口",
        ],
    },
    "oom_event": {
        "pattern": r"OOM.*事件.*?(\d+)",
        "suggestion": [
            "系统发生 Out of Memory 事件，进程被系统杀死",
            "建议:",
            "  1. 查看被杀进程日志: dmesg | grep -i 'killed process'",
            "  2. 增加物理内存或 swap 空间",
            "  3. 限制应用程序内存使用（如 Java -Xmx 参数）",
            "  4. 配置 systemd 服务的 MemoryLimit",
        ],
    },
    "disk_io_error": {
        "pattern": r"磁盘.*错误.*?(\d+)",
        "suggestion": [
            "检测到磁盘 I/O 错误，可能磁盘存在物理问题",
            "建议:",
            "  1. 使用 'smartctl -a /dev/sda' 检查磁盘 SMART 状态",
            "  2. 使用 'dmesg | grep -i error' 查看详细错误信息",
            "  3. 备份重要数据",
            "  4. 使用 'fsck' 检查文件系统（需要在卸载状态下进行）",
        ],
    },
    "service_crash": {
        "pattern": r"服务崩溃.*?(\d+)",
        "suggestion": [
            "检测到服务崩溃或内核错误",
            "建议:",
            "  1. 查看崩溃日志: journalctl -xe",
            "  2. 查看内核日志: dmesg | tail -50",
            "  3. 检查服务配置是否正确: systemctl status <service>",
            "  4. 使用 'coredumpctl list' 查看 core dump 记录",
        ],
    },
    "service_inactive": {
        "pattern": r"服务 (\S+) 未运行",
        "suggestion": [
            "关键服务未运行，可能影响系统功能",
            "建议:",
            "  1. 使用 'systemctl status <service>' 查看服务详细状态",
            "  2. 尝试启动服务: systemctl start <service>",
            "  3. 查看服务日志: journalctl -u <service> -n 50",
            "  4. 检查 /etc/systemd/system/ 下服务配置文件",
        ],
    },
    "port_not_listen": {
        "pattern": r"端口 (\S+) 未监听",
        "suggestion": [
            "预期端口未被监听，相关服务可能未启动或配置错误",
            "建议:",
            "  1. 检查服务是否启动: systemctl status <service>",
            "  2. 检查服务配置文件中监听地址和端口是否正确",
            "  3. 使用 'netstat -tlnp | grep :<port>' 确认端口状态",
            "  4. 检查防火墙规则: iptables -L -n",
        ],
    },
    "anomaly_high": {
        "pattern": r"异常占比偏高",
        "suggestion": [
            "日志异常占比偏高，系统可能存在问题",
            "建议:",
            "  1. 重点排查高频错误类型",
            "  2. 查看异常发生的时间段，寻找关联事件",
            "  3. 检查系统资源使用趋势",
            "  4. 考虑增加监控频率，收集更多数据",
        ],
    },
    "zombie_process": {
        "pattern": r"僵尸进程",
        "suggestion": [
            "发现僵尸进程，可能由父进程未正确处理子进程退出导致",
            "建议:",
            "  1. 使用 'ps aux | grep Z' 查看僵尸进程详情",
            "  2. 找到僵尸进程的父进程并重启",
            "  3. 如果是长期僵尸进程，考虑重启服务器",
        ],
    },
}

# 通用诊断（当没有匹配特定规则时）
DEFAULT_SUGGESTION = [
    "系统巡检完成，未匹配到特定异常模式",
    "建议:",
    "  1. 定期执行巡检以建立系统基线数据",
    "  2. 对比历史报告发现趋势变化",
    "  3. 关注磁盘和内存使用趋势",
]


def parse_input(input_text: str) -> list:
    """分析输入文本，匹配诊断规则"""
    diagnoses = []
    matched = set()

    for rule_name, rule in DIAGNOSIS_RULES.items():
        match = re.search(rule["pattern"], input_text, re.IGNORECASE)
        if match:
            diagnoses.append({
                "rule": rule_name,
                "match": match.group(0),
                "suggestion": rule["suggestion"],
            })
            matched.add(rule_name)

    if not diagnoses:
        diagnoses.append({
            "rule": "default",
            "match": "无特定异常",
            "suggestion": DEFAULT_SUGGESTION,
        })

    return diagnoses


def format_diagnosis(diagnoses: list) -> str:
    """格式化输出诊断建议"""
    lines = []
    lines.append("# 诊断建议报告")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    for i, diag in enumerate(diagnoses, 1):
        lines.append(f"## 诊断 {i}: {diag['match']}")
        lines.append("")
        for line in diag["suggestion"]:
            lines.append(line)
        lines.append("")

    lines.append("---")
    lines.append("*注意: 以上建议为基于巡检数据的自动分析，实际操作前请确认环境状态*")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Linux 运维智能巡检 - 诊断建议生成模块"
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="巡检结果文件路径（不指定则从 stdin 读取）",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="诊断报告输出路径（默认输出到 stdout）",
    )

    args = parser.parse_args()

    # 读取输入
    if args.input and os.path.isfile(args.input):
        with open(args.input, "r", encoding="utf-8", errors="replace") as f:
            input_text = f.read()
    elif not sys.stdin.isatty():
        input_text = sys.stdin.read()
    else:
        print("错误: 未指定输入文件或管道输入", file=sys.stderr)
        print("用法: diagnose.py --input <巡检结果文件>", file=sys.stderr)
        print("或: cat check_result.log | diagnose.py", file=sys.stderr)
        sys.exit(1)

    # 执行诊断
    diagnoses = parse_input(input_text)
    report = format_diagnosis(diagnoses)

    # 输出结果
    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"诊断报告已保存至: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
