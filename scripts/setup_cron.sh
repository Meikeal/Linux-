#!/bin/bash
# =============================================================================
# setup_cron.sh - crontab 定时任务配置脚本
# 支持安装、查看、移除定时巡检任务
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPS_ASSIST="${SCRIPT_DIR}/ops-assist"
CRON_MARKER="# ops-assist-auto-check"
CRON_ENTRY=""

print_help() {
    cat << EOF
用法: ./setup_cron.sh <command> [options]

命令:
  install     安装定时巡检任务
  uninstall   移除定时巡检任务
  show        显示当前配置的定时任务
  status      查看定时巡检任务状态

选项:
  -i, --interval <time>  巡检间隔 (默认: daily)
                          可用值: hourly, daily, 12h, custom
  -c, --cron <expr>      自定义 cron 表达式 (仅 custom 模式)
  --dry-run               仅显示将要执行的操作，不实际修改 crontab

示例:
  ./setup_cron.sh install                      # 安装每日巡检（默认）
  ./setup_cron.sh install -i hourly            # 安装每小时巡检
  ./setup_cron.sh install -i custom -c "0 */6 * * *"  # 自定义：每6小时
  ./setup_cron.sh show                         # 查看当前定时任务
  ./setup_cron.sh uninstall                    # 移除定时巡检
EOF
}

get_cron_entry() {
    local interval="${1:-daily}"
    local log_dir="${SCRIPT_DIR}/logs"
    local report_dir="${SCRIPT_DIR}/reports"

    case "${interval}" in
        hourly)
            # 每小时第5分钟执行
            echo "5 * * * * cd ${SCRIPT_DIR} && bash ${OPS_ASSIST} all >> ${log_dir}/cron_run.log 2>&1 ${CRON_MARKER}"
            ;;
        daily)
            # 每天凌晨2点执行
            echo "0 2 * * * cd ${SCRIPT_DIR} && bash ${OPS_ASSIST} all >> ${log_dir}/cron_run.log 2>&1 ${CRON_MARKER}"
            ;;
        12h)
            # 每12小时（8点和20点）
            echo "0 8,20 * * * cd ${SCRIPT_DIR} && bash ${OPS_ASSIST} all >> ${log_dir}/cron_run.log 2>&1 ${CRON_MARKER}"
            ;;
        custom)
            local cron_expr="${2:-0 2 * * *}"
            echo "${cron_expr} cd ${SCRIPT_DIR} && bash ${OPS_ASSIST} all >> ${log_dir}/cron_run.log 2>&1 ${CRON_MARKER}"
            ;;
        *)
            echo "[ERROR] 不支持的间隔: ${interval}" >&2
            return 1
            ;;
    esac
}

install_cron() {
    local interval="daily"
    local custom_cron=""
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -i|--interval)
                interval="$2"
                shift 2
                ;;
            -c|--cron)
                custom_cron="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    CRON_ENTRY=$(get_cron_entry "${interval}" "${custom_cron}")
    if [[ $? -ne 0 ]]; then
        return 1
    fi

    echo "定时巡检任务配置:"
    echo "  项目目录: ${SCRIPT_DIR}"
    echo "  间隔: ${interval}"
    echo "  cron 条目: ${CRON_ENTRY%%#*}"
    echo ""

    if [[ "${dry_run}" == "true" ]]; then
        echo "[DRY-RUN] 将添加以下 cron 条目:"
        echo "  ${CRON_ENTRY}"
        return 0
    fi

    # 检查是否已安装
    if crontab -l 2>/dev/null | grep -qF "${CRON_MARKER}"; then
        echo "[WARN] 已存在 ops-assist 定时任务，请先执行 uninstall 移除"
        echo "当前定时任务:"
        crontab -l 2>/dev/null | grep -F "${CRON_MARKER}"
        echo ""
        echo "如需重新安装，请运行: ./setup_cron.sh uninstall && ./setup_cron.sh install"
        return 1
    fi

    # 添加到 crontab
    (crontab -l 2>/dev/null || true; echo "${CRON_ENTRY}") | crontab -
    echo "[SUCCESS] 定时巡检任务已安装"
    echo ""
    echo "查看任务: crontab -l"
    echo "查看运行日志: ${SCRIPT_DIR}/logs/cron_run.log"
}

uninstall_cron() {
    local dry_run=false
    [[ "$1" == "--dry-run" ]] && dry_run=true

    if ! crontab -l 2>/dev/null | grep -qF "${CRON_MARKER}"; then
        echo "[INFO] 未找到 ops-assist 定时任务"
        return 0
    fi

    echo "当前定时任务:"
    crontab -l 2>/dev/null | grep -F "${CRON_MARKER}"
    echo ""

    if [[ "${dry_run}" == "true" ]]; then
        echo "[DRY-RUN] 将移除以上定时任务"
        return 0
    fi

    crontab -l 2>/dev/null | grep -vF "${CRON_MARKER}" | crontab -
    echo "[SUCCESS] 定时巡检任务已移除"
}

show_cron() {
    echo "当前用户定时任务:"
    echo "========================================="
    local crons
    crons=$(crontab -l 2>/dev/null || true)
    if [[ -z "${crons}" ]]; then
        echo "  (无定时任务)"
    else
        echo "${crons}"
    fi
    echo "========================================="
}

check_status() {
    echo "ops-assist 定时巡检状态:"
    echo "========================================="

    # 检查 crontab 中是否有我们的任务
    if crontab -l 2>/dev/null | grep -qF "${CRON_MARKER}"; then
        echo "  定时任务: [已安装]"
        crontab -l 2>/dev/null | grep -F "${CRON_MARKER}" | while read -r line; do
            echo "    条目: ${line%#*}"
        done
    else
        echo "  定时任务: [未安装]"
    fi

    # 检查运行日志
    local log_file="${SCRIPT_DIR}/logs/cron_run.log"
    if [[ -f "${log_file}" ]]; then
        echo "  运行日志: ${log_file}"
        local last_run
        last_run=$(grep "开始完整巡检流程" "${log_file}" 2>/dev/null | tail -1 | sed 's/.*(\(.*\)).*/\1/' || echo "无记录")
        echo "  最近运行: ${last_run}"
        local run_count
        run_count=$(grep -c "完整巡检流程完成" "${log_file}" 2>/dev/null || echo "0")
        echo "  运行次数: ${run_count}"
    else
        echo "  运行日志: 暂无"
    fi

    # 检查报告目录
    local report_dir="${SCRIPT_DIR}/reports"
    if [[ -d "${report_dir}" ]]; then
        local report_count
        report_count=$(find "${report_dir}" -name "report_*.md" -o -name "report_*.html" 2>/dev/null | wc -l)
        echo "  报告数量: ${report_count}"
    fi

    echo "========================================="
}

# 主入口
main() {
    local command="${1:-help}"
    shift 2>/dev/null || true

    case "${command}" in
        install)
            install_cron "$@"
            ;;
        uninstall|remove)
            uninstall_cron "$@"
            ;;
        show|list)
            show_cron
            ;;
        status)
            check_status
            ;;
        help|--help|-h)
            print_help
            ;;
        *)
            echo "[ERROR] 未知命令: ${command}"
            print_help
            exit 1
            ;;
    esac
}

main "$@"
