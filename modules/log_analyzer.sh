#!/bin/bash
# =============================================================================
# log_analyzer.sh - 日志异常分析模块
# 使用 grep/sed/awk 进行日志过滤和异常统计
# =============================================================================

set -euo pipefail

SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CONFIG_FILE="${SCRIPT_DIR}/config/ops-assist.conf"

# 加载配置中的日志关键词
LOG_PATTERNS="${LOG_PATTERNS:-error|failed|denied|timeout|disconnect|refused|panic|OOM|segfault}"

# 输出目标和日志文件由 main 统一解析
OUTPUT_FILE="/dev/stdout"
LOG_FILE=""

# 统计结果
TOTAL_LINES=0
ANOMALY_COUNT=0

# =============================================================================
# 辅助函数
# =============================================================================
write_output() {
    echo "$1" >> "${OUTPUT_FILE}"
}

log_section() {
    write_output ""
    write_output "========================================"
    write_output "  ${1}"
    write_output "========================================"
}

# =============================================================================
# 检查日志文件
# =============================================================================
validate_log_file() {
    if [[ -z "${LOG_FILE}" ]]; then
        # 尝试默认日志文件
        local candidates=(
            "/var/log/syslog"
            "/var/log/messages"
            "${SCRIPT_DIR}/samples/sample_logs/syslog_sample.log"
        )
        for candidate in "${candidates[@]}"; do
            if [[ -f "${candidate}" ]] && [[ -r "${candidate}" ]]; then
                LOG_FILE="${candidate}"
                break
            fi
        done
    fi

    if [[ -z "${LOG_FILE}" ]]; then
        write_output "[ERROR] 未指定日志文件，且找不到默认日志文件"
        write_output "用法: log_analyzer.sh <output_file> <log_file>"
        write_output "  -f <log_file> 指定要分析的日志文件"
        return 1
    fi

    if [[ ! -f "${LOG_FILE}" ]]; then
        write_output "[ERROR] 日志文件不存在: ${LOG_FILE}"
        return 1
    fi

    if [[ ! -r "${LOG_FILE}" ]]; then
        write_output "[ERROR] 日志文件无读取权限: ${LOG_FILE}"
        write_output "[提示] 请使用 sudo 运行，或使用样例日志测试: samples/sample_logs/"
        return 1
    fi

    return 0
}

# =============================================================================
# 基本信息
# =============================================================================
analyze_basic_info() {
    log_section "日志文件基本信息"

    write_output "  文件路径: ${LOG_FILE}"
    write_output "  文件大小: $(du -h "${LOG_FILE}" 2>/dev/null | cut -f1)"
    TOTAL_LINES=$(wc -l < "${LOG_FILE}" 2>/dev/null | tr -d '[:space:]')
    [[ -z "${TOTAL_LINES}" ]] && TOTAL_LINES=0
    write_output "  总行数: ${TOTAL_LINES}"

    # 获取日志时间范围
    local first_line last_line
    first_line=$(head -1 "${LOG_FILE}" 2>/dev/null | sed 's/^[^0-9]*//')
    last_line=$(tail -1 "${LOG_FILE}" 2>/dev/null | sed 's/^[^0-9]*//')
    write_output "  首条记录: ${first_line:-N/A}"
    write_output "  末条记录: ${last_line:-N/A}"
}

# =============================================================================
# 关键词过滤与统计
# =============================================================================
analyze_keywords() {
    log_section "异常关键词分析"

    write_output "  搜索关键词: $(echo "${LOG_PATTERNS}" | sed 's/|/ /g')"
    write_output ""

    # 提取每种关键词的匹配行数
    local total_anomalies=0
    declare -A keyword_counts

    # 拆分关键词并逐个统计
    local IFS='|'
    for keyword in ${LOG_PATTERNS}; do
        local count
        count=$( (grep -ci "${keyword}" "${LOG_FILE}" 2>/dev/null || true) | head -1)
        count=$(echo "${count}" | tr -d '[:space:]')
        [[ -z "${count}" ]] && count=0
        keyword_counts["${keyword}"]=${count}
        total_anomalies=$((total_anomalies + count))
    done
    IFS=' '

    # 按数量降序输出
    write_output "  关键词匹配统计:"
    for keyword in "${!keyword_counts[@]}"; do
        echo "    ${keyword}: ${keyword_counts[${keyword}]}"
    done | sort -t: -k2 -rn >> "${OUTPUT_FILE}"

    ANOMALY_COUNT=${total_anomalies}
    local anomaly_rate=0
    if [[ ${TOTAL_LINES} -gt 0 ]]; then
        anomaly_rate=$(( (total_anomalies * 100) / TOTAL_LINES ))
    fi

    write_output ""
    write_output "  异常事件总数: ${total_anomalies}"
    write_output "  异常占比: ${anomaly_rate}%"

    if [[ ${total_anomalies} -eq 0 ]]; then
        write_output "  [OK] 未发现异常关键词"
    elif [[ ${anomaly_rate} -ge 10 ]]; then
        write_output "  [WARN] 异常占比偏高，建议进一步排查"
    else
        write_output "  [INFO] 异常占比在正常范围内"
    fi
}

# =============================================================================
# 高频错误 TOP 10
# =============================================================================
analyze_top_errors() {
    log_section "高频错误排行 (TOP 10)"

    write_output "  出现频率最高的异常日志:"
    write_output ""

    # 提取匹配行，取出现最多的前10条
    grep -iE "${LOG_PATTERNS}" "${LOG_FILE}" 2>/dev/null | \
        sed 's/^.*[0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}//' | \
        sed 's/^[[:space:]]*//' | \
        sort | uniq -c | sort -rn | head -10 | \
        awk '{
            count=$1; $1="";
            line=substr($0,2);
            # 截断过长的行
            if (length(line) > 120) line=substr(line,1,120)"...";
            printf "    [%s次] %s\n", count, line
        }' >> "${OUTPUT_FILE}"
}

# =============================================================================
# 时间分布分析
# =============================================================================
analyze_time_distribution() {
    log_section "异常时间分布"

    # 尝试提取小时信息进行分布统计
    local hour_pattern='[0-9]{2}:[0-9]{2}:[0-9]{2}'

    # 检查是否有带时间戳的日志行
    local timed_lines
    timed_lines=$( (grep -cE "^[A-Z][a-z]{2} [0-9]|^[0-9]{4}-[0-9]{2}-[0-9]{2}|^[A-Z][a-z]{2} [ :0-9]{11}" "${LOG_FILE}" 2>/dev/null || true) | head -1)

    if [[ ${timed_lines} -gt 0 ]]; then
        write_output "  异常事件按小时分布:"
        write_output ""
        grep -iE "${LOG_PATTERNS}" "${LOG_FILE}" 2>/dev/null | \
            grep -oE '[0-9]{2}:[0-9]{2}:[0-9]{2}' | \
            cut -d: -f1 | sort | uniq -c | \
            awk '{
                count=$1; hour=$2;
                if (count > 10) status="[WARN]";
                else status="[OK]  ";
                printf "    %02d:00 - %s (%d条)\n", hour, status, count
            }' >> "${OUTPUT_FILE}"
    else
        write_output "  无法识别日志时间戳格式，跳过时间分布分析"
    fi
}

# =============================================================================
# 特定模式检测
# =============================================================================
analyze_patterns() {
    log_section "特定模式检测"

    # SSH 登录失败
    local ssh_failed
    ssh_failed=$( (grep -ciE "Failed password|authentication failure|Failed publickey" "${LOG_FILE}" 2>/dev/null || true) | head -1)
    write_output "  SSH 登录失败次数: ${ssh_failed}"
    if [[ ${ssh_failed} -ge 10 ]]; then
        write_output "  [WARN] SSH 失败登录次数较多，可能存在暴力破解"
    fi

    # OOM 事件
    local oom_count
    oom_count=$( (grep -ciE "Out of memory|OOM|invoked oom-killer" "${LOG_FILE}" 2>/dev/null || true) | head -1)
    write_output "  OOM (内存溢出) 事件: ${oom_count}"
    if [[ ${oom_count} -gt 0 ]]; then
        write_output "  [WARN] 检测到 OOM 事件，建议检查内存使用情况"
    fi

    # 磁盘错误
    local disk_err
    disk_err=$( (grep -ciE "I/O error|EXT.*error|read-only|block error" "${LOG_FILE}" 2>/dev/null || true) | head -1)
    write_output "  磁盘 I/O 错误: ${disk_err}"
    if [[ ${disk_err} -gt 0 ]]; then
        write_output "  [WARN] 检测到磁盘 I/O 错误，建议检查磁盘健康状态"
    fi

    # 服务崩溃
    local service_crash
    service_crash=$( (grep -ciE "segfault|core dumped|oops|kernel BUG|panic" "${LOG_FILE}" 2>/dev/null || true) | head -1)
    write_output "  服务崩溃/内核错误: ${service_crash}"
    if [[ ${service_crash} -gt 0 ]]; then
        write_output "  [WARN] 检测到服务崩溃或内核错误，建议立即排查"
    fi
}

# =============================================================================
# 异常上下文提取
# =============================================================================
analyze_context() {
    log_section "异常上下文样本 (前5条)"

    write_output "  （展示异常日志的前后上下文）"
    write_output ""

    local first_anomaly_line
    first_anomaly_line=$(grep -niE "${LOG_PATTERNS}" "${LOG_FILE}" 2>/dev/null | head -5 | cut -d: -f1 | head -1)

    if [[ -n "${first_anomaly_line}" ]]; then
        local start_line=$(( first_anomaly_line - 2 ))
        [[ ${start_line} -lt 1 ]] && start_line=1
        sed -n "${start_line},$((start_line + 20))p" "${LOG_FILE}" 2>/dev/null | \
            while IFS= read -r line; do
                if echo "${line}" | grep -qiE "${LOG_PATTERNS}"; then
                    write_output "  >>> ${line}"
                else
                    write_output "      ${line}"
                fi
            done
    else
        write_output "  （未找到异常日志行）"
    fi
}

# =============================================================================
# 主函数
# =============================================================================
main() {
    # 解析参数
    local positional_count=0
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -f|--log-file)
                LOG_FILE="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            *)
                positional_count=$((positional_count + 1))
                if [[ ${positional_count} -eq 1 ]]; then
                    OUTPUT_FILE="$1"
                elif [[ ${positional_count} -eq 2 ]]; then
                    LOG_FILE="$1"
                fi
                shift
                ;;
        esac
    done

    # 确保输出目录存在
    local out_dir
    out_dir=$(dirname "${OUTPUT_FILE}")
    if [[ "${out_dir}" != "." && "${out_dir}" != "/dev" && ! -d "${out_dir}" ]]; then
        mkdir -p "${out_dir}" 2>/dev/null || true
    fi

    if [[ "${OUTPUT_FILE}" != "/dev/stdout" ]]; then
        : > "${OUTPUT_FILE}"
    fi

    # 写入报告头
    write_output "# 日志异常分析报告"
    write_output "> 生成时间: $(date '+%Y-%m-%d %H:%M:%S')"

    # 验证日志文件
    if ! validate_log_file; then
        return 1
    fi

    # 执行分析
    analyze_basic_info
    analyze_keywords
    analyze_top_errors
    analyze_time_distribution
    analyze_patterns
    analyze_context

    log_section "分析完成"
    write_output "  总行数: ${TOTAL_LINES}"
    write_output "  异常事件: ${ANOMALY_COUNT}"
    write_output ""
}

# 如果直接执行此脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
