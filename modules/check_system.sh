#!/bin/bash
# =============================================================================
# check_system.sh - 系统状态巡检模块
# 采集 CPU、内存、磁盘、进程、端口和服务状态
# =============================================================================

set -euo pipefail

# 脚本所在目录（被主脚本调用时通过环境变量传递）
SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CONFIG_FILE="${SCRIPT_DIR}/config/ops-assist.conf"

# 加载配置
if [[ -f "${CONFIG_FILE}" ]]; then
    source "${CONFIG_FILE}"
fi

# 默认阈值
DISK_WARN="${DISK_WARN_THRESHOLD:-80}"
DISK_CRITICAL="${DISK_CRITICAL_THRESHOLD:-90}"
MEM_WARN="${MEM_WARN_THRESHOLD:-80}"
MEM_CRITICAL="${MEM_CRITICAL_THRESHOLD:-90}"
CPU_LOAD_WARN="${CPU_LOAD_WARN:-2.0}"
WATCH_SERVICES="${WATCH_SERVICES:-ssh nginx apache2 docker}"
WATCH_PORTS="${WATCH_PORTS:-22 80 443 3306 8080}"
HEALTH_URLS="${HEALTH_URLS:-}"

# 输出目标
OUTPUT_FILE="${1:-/dev/stdout}"

# 状态标记
ISSUES_FOUND=0

# =============================================================================
# 辅助函数
# =============================================================================
write_output() {
    echo "$1" >> "${OUTPUT_FILE}"
}

log_section() {
    local title="$1"
    write_output ""
    write_output "========================================"
    write_output "  ${title}"
    write_output "========================================"
}

log_ok() {
    write_output "  [OK] $1"
}

log_warn() {
    write_output "  [WARN] $1"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
}

log_error() {
    write_output "  [ERROR] $1"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
}

# 检查命令是否存在
cmd_exists() {
    command -v "$1" >/dev/null 2>&1
}

# =============================================================================
# 1. 系统基本信息
# =============================================================================
check_system_info() {
    log_section "系统基本信息"

    write_output "  主机名: $(hostname 2>/dev/null || echo 'N/A')"
    write_output "  内核版本: $(uname -r 2>/dev/null || echo 'N/A')"
    write_output "  系统版本: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2 || echo 'N/A')"
    write_output "  运行时间: $(uptime -p 2>/dev/null | sed 's/up //' || echo 'N/A')"
    write_output "  当前时间: $(date '+%Y-%m-%d %H:%M:%S')"
}

# =============================================================================
# 2. CPU 使用率和负载
# =============================================================================
check_cpu() {
    log_section "CPU 状态"

    if cmd_exists mpstat; then
        write_output "  CPU 使用率:"
        mpstat 1 1 2>/dev/null | tail -1 | awk '{
            printf "    用户态: %.1f%%  系统态: %.1f%%  空闲: %.1f%%\n", $3, $5, $12
        }' >> "${OUTPUT_FILE}"
    elif cmd_exists top; then
        local cpu_idle
        cpu_idle=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{print $8}' | cut -d'%' -f1 || echo "")
        if [[ -n "${cpu_idle}" ]]; then
            local cpu_used
            cpu_used=$(echo "100 - ${cpu_idle}" | bc 2>/dev/null || echo "N/A")
            write_output "  CPU 使用率: ${cpu_used}% (空闲: ${cpu_idle}%)"
        fi
    else
        write_output "  CPU 使用率: 无法获取"
    fi

    # 系统负载
    local load
    load=$(uptime 2>/dev/null | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',' || echo "0")
    write_output "  系统负载 (1min): ${load}"

    if [[ -n "${load}" && "${load}" != "0" ]]; then
        if echo "${load} > ${CPU_LOAD_WARN}" | bc -l 2>/dev/null | grep -q 1; then
            log_warn "系统负载偏高 (当前: ${load}, 阈值: ${CPU_LOAD_WARN})"
        else
            log_ok "系统负载正常"
        fi
    fi

    # CPU 核心数
    local cpu_cores
    cpu_cores=$(nproc 2>/dev/null || echo "N/A")
    write_output "  CPU 核心数: ${cpu_cores}"
}

# =============================================================================
# 3. 内存使用情况
# =============================================================================
check_memory() {
    log_section "内存状态"

    if cmd_exists free; then
        local total used free avail swap_total swap_used
        read -r total used free avail <<< $(free -m 2>/dev/null | awk '/^Mem:/{print $2, $3, $4, $7}')
        read -r swap_total swap_used <<< $(free -m 2>/dev/null | awk '/^Swap:/{print $2, $3}')

        local mem_usage=$(( (used * 100) / total ))

        write_output "  总内存: ${total}MB"
        write_output "  已用内存: ${used}MB (${mem_usage}%)"
        write_output "  可用内存: ${avail:-${free}}MB"
        write_output "  Swap 总量: ${swap_total:-0}MB"
        write_output "  Swap 已用: ${swap_used:-0}MB"

        if [[ ${mem_usage} -ge ${MEM_CRITICAL} ]]; then
            log_error "内存使用率过高 (${mem_usage}% >= ${MEM_CRITICAL}%)"
        elif [[ ${mem_usage} -ge ${MEM_WARN} ]]; then
            log_warn "内存使用率偏高 (${mem_usage}% >= ${MEM_WARN}%)"
        else
            log_ok "内存使用率正常 (${mem_usage}%)"
        fi
    else
        write_output "  内存信息: 无法获取（free 命令不可用）"
    fi
}

# =============================================================================
# 4. 磁盘分区使用率
# =============================================================================
check_disk() {
    log_section "磁盘状态"

    if cmd_exists df; then
        write_output "  分区使用情况:"
        df -hP 2>/dev/null | awk 'NR > 1 && $0 !~ /tmpfs|devtmpfs|efivarfs|snapfuse|squashfs|udev/ {
            mount=$NF; usage=$(NF-1); avail=$(NF-2); used=$(NF-3); size=$(NF-4);
            fs=$1; for (i=2; i<=NF-5; i++) fs=fs" "$i;
            printf "%s\t%s\t%s\t%s\n", mount, used, size, usage;
        }' | \
        while IFS=$'\t' read -r mount used size usage; do
            write_output "    ${mount}: ${used}/${size} (${usage})"

            local usage_num="${usage%\%}"
            if [[ "${usage_num}" =~ ^[0-9]+$ ]]; then
                if [[ ${usage_num} -ge ${DISK_CRITICAL} ]]; then
                    log_error "磁盘使用率过高: ${mount} (${usage})"
                elif [[ ${usage_num} -ge ${DISK_WARN} ]]; then
                    log_warn "磁盘使用率偏高: ${mount} (${usage})"
                fi
            fi
        done
    else
        write_output "  磁盘信息: 无法获取（df 命令不可用）"
        return
    fi

    # inode 使用情况
    write_output ""
    write_output "  Inode 使用情况:"
    df -iP 2>/dev/null | awk 'NR > 1 && $0 !~ /tmpfs|devtmpfs|efivarfs|snapfuse|squashfs|udev/ {
        mount=$NF; iusage=$(NF-1);
        printf "%s\t%s\n", mount, iusage;
    }' | \
    while IFS=$'\t' read -r mount iusage; do
        local iusage_num="${iusage%\%}"
        if [[ "${iusage_num}" =~ ^[0-9]+$ ]] && [[ ${iusage_num} -ge 80 ]]; then
            log_warn "Inode 使用率偏高: ${mount} (${iusage})"
        fi
    done
}

# =============================================================================
# 5. 关键进程状态
# =============================================================================
check_processes() {
    log_section "进程状态"

    if cmd_exists ps; then
        # 进程总数
        local proc_count
        proc_count=$(ps aux 2>/dev/null | wc -l)
        write_output "  进程总数: ${proc_count}"

        # CPU 占用最高的进程
        write_output ""
        write_output "  CPU 占用 TOP 5:"
        ps aux 2>/dev/null | sort -k3 -rn | head -5 | awk '{
            printf "    PID: %-6s  CPU: %-5s  MEM: %-5s  %s\n", $2, $3, $4, $11
        }' >> "${OUTPUT_FILE}" || write_output "    (无法获取进程详情)"

        # 内存占用最高的进程
        write_output ""
        write_output "  内存占用 TOP 5:"
        ps aux 2>/dev/null | sort -k4 -rn | head -5 | awk '{
            printf "    PID: %-6s  CPU: %-5s  MEM: %-5s  %s\n", $2, $3, $4, $11
        }' >> "${OUTPUT_FILE}" || write_output "    (无法获取进程详情)"

        # 僵尸进程检查
        local zombie_count
        zombie_count=$(ps aux 2>/dev/null | awk '$8 ~ /Z/ {count++} END {print count+0}')
        if [[ ${zombie_count} -gt 0 ]]; then
            log_warn "发现 ${zombie_count} 个僵尸进程"
        else
            log_ok "无僵尸进程"
        fi
    else
        write_output "  进程信息: 无法获取"
    fi
}

# =============================================================================
# 6. 监听端口
# =============================================================================
check_ports() {
    log_section "端口状态"

    local port_cmd=""
    if cmd_exists ss; then
        port_cmd="ss -tlnp"
    elif cmd_exists netstat; then
        port_cmd="netstat -tlnp"
    else
        write_output "  端口信息: 无法获取（ss/netstat 均不可用）"
        return
    fi

    write_output "  配置监控端口: ${WATCH_PORTS}"
    write_output ""

    for port in ${WATCH_PORTS}; do
        if ${port_cmd} 2>/dev/null | grep -q ":${port} "; then
            local proc_info
            proc_info=$(${port_cmd} 2>/dev/null | grep ":${port} " | awk '{print $NF}' | head -1)
            log_ok "端口 ${port} 正在监听 (进程: ${proc_info})"
        else
            log_warn "端口 ${port} 未监听"
        fi
    done
}

# =============================================================================
# 7. systemd 服务状态
# =============================================================================
check_services() {
    log_section "服务状态"

    if ! cmd_exists systemctl; then
        write_output "  服务信息: systemctl 不可用（非 systemd 系统）"
        return
    fi

    write_output "  配置监控服务: ${WATCH_SERVICES}"
    write_output ""

    for svc in ${WATCH_SERVICES}; do
        # 检查服务是否存在
        if systemctl list-unit-files "${svc}.service" 2>/dev/null | grep -q "${svc}"; then
            if systemctl is-active --quiet "${svc}" 2>/dev/null; then
                log_ok "服务 ${svc} 运行中"
            else
                local status
                status=$(systemctl is-active "${svc}" 2>/dev/null || echo "unknown")
                if [[ "${status}" == "failed" ]]; then
                    log_error "服务 ${svc} 运行失败 (status: ${status})"
                else
                    log_warn "服务 ${svc} 未运行 (status: ${status})"
                fi
            fi
        else
            write_output "  [SKIP] 服务 ${svc} 不存在，跳过检查"
        fi
    done
}

# =============================================================================
# 8. 网络连接状态
# =============================================================================
check_network() {
    log_section "网络状态"

    if cmd_exists ss; then
        local established listen time_wait
        established=$(ss -tan state established 2>/dev/null | tail -n +2 | wc -l)
        listen=$(ss -tan state listen 2>/dev/null | tail -n +2 | wc -l)
        time_wait=$(ss -tan state time-wait 2>/dev/null | tail -n +2 | wc -l)
        write_output "  TCP 连接: ESTABLISHED=${established}  LISTEN=${listen}  TIME_WAIT=${time_wait}"
    elif cmd_exists netstat; then
        local established listen
        established=$(netstat -tan 2>/dev/null | grep ESTABLISHED | wc -l)
        listen=$(netstat -tan 2>/dev/null | grep LISTEN | wc -l)
        write_output "  TCP 连接: ESTABLISHED=${established}  LISTEN=${listen}"
    else
        write_output "  网络信息: 无法获取"
    fi
}

# =============================================================================
# 9. Web 健康检查
# =============================================================================
check_health_urls() {
    log_section "Web 健康检查"

    if [[ -z "${HEALTH_URLS// }" ]]; then
        write_output "  未配置 HEALTH_URLS，跳过 HTTP 健康检查"
        return
    fi

    if ! cmd_exists curl && ! cmd_exists wget; then
        write_output "  健康检查: 无法获取（curl/wget 均不可用）"
        return
    fi

    write_output "  配置健康检查地址: ${HEALTH_URLS}"
    write_output ""

    for url in ${HEALTH_URLS}; do
        local response=""
        if cmd_exists curl; then
            response=$(curl -fsS --max-time 5 "${url}" 2>/dev/null || true)
        else
            response=$(wget -q -T 5 -O - "${url}" 2>/dev/null || true)
        fi

        if [[ "${response}" == *"ok"* ]]; then
            log_ok "健康检查通过: ${url}"
        else
            log_warn "健康检查失败: ${url}"
        fi
    done
}

# =============================================================================
# 主函数
# =============================================================================
main() {
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
    write_output "# 系统状态巡检报告"
    write_output "> 生成时间: $(date '+%Y-%m-%d %H:%M:%S')"

    # 执行各项检查
    check_system_info
    check_cpu
    check_memory
    check_disk
    check_processes
    check_ports
    check_services
    check_network
    check_health_urls

    # 汇总
    log_section "巡检汇总"
    if [[ ${ISSUES_FOUND} -eq 0 ]]; then
        log_ok "未发现异常，系统状态良好"
    else
        log_warn "共发现 ${ISSUES_FOUND} 个需要注意的问题"
    fi

    write_output ""
    return 0
}

# 如果直接执行此脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
