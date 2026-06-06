#!/bin/bash
# =============================================================================
# deploy_blog.sh - 将 web-blog 动态博客部署为 Linux systemd 服务
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLOG_SRC="${SCRIPT_DIR}/web-blog"
SERVICE_SRC="${SCRIPT_DIR}/config/ops-blog.service"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/ops-blog}"
SERVICE_NAME="${SERVICE_NAME:-ops-blog}"
PORT="${PORT:-80}"

print_info() {
    echo "[INFO] $1"
}

print_success() {
    echo "[SUCCESS] $1"
}

print_error() {
    echo "[ERROR] $1" >&2
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        print_error "缺少命令: $1"
        exit 1
    fi
}

ensure_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        print_error "部署需要 root 权限，请使用 sudo 运行: sudo ./scripts/deploy_blog.sh install"
        exit 1
    fi
}

install_blog() {
    ensure_root
    require_cmd python3
    require_cmd systemctl

    if [[ ! -d "${BLOG_SRC}" ]]; then
        print_error "博客目录不存在: ${BLOG_SRC}"
        exit 1
    fi

    print_info "部署动态博客文件到 ${DEPLOY_DIR}"
    mkdir -p "${DEPLOY_DIR}"
    cp -R "${BLOG_SRC}/." "${DEPLOY_DIR}/"

    chmod -R a+rX "${DEPLOY_DIR}"

    print_info "安装 systemd 服务: ${SERVICE_NAME}"
    sed "s/8080/${PORT}/g" "${SERVICE_SRC}" > "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    systemctl restart "${SERVICE_NAME}"

    print_success "博客服务已启动"
    systemctl --no-pager --full status "${SERVICE_NAME}" || true
    echo ""
    print_info "本机验证: curl http://127.0.0.1:${PORT}/healthz.txt"
    for _ in 1 2 3 4 5; do
        if curl -fsS "http://127.0.0.1:${PORT}/healthz.txt" >/dev/null 2>&1; then
            print_success "健康检查通过: http://127.0.0.1:${PORT}/healthz.txt"
            return
        fi
        sleep 1
    done
    print_error "健康检查暂未通过，请稍后执行: curl http://127.0.0.1:${PORT}/healthz.txt"
    return 1
}

status_blog() {
    require_cmd systemctl
    systemctl --no-pager --full status "${SERVICE_NAME}"
}

logs_blog() {
    require_cmd journalctl
    journalctl -u "${SERVICE_NAME}" -n 80 --no-pager
}

uninstall_blog() {
    ensure_root
    require_cmd systemctl

    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload

    print_success "已移除 ${SERVICE_NAME} systemd 服务，博客文件仍保留在 ${DEPLOY_DIR}"
}

show_help() {
    cat << EOF
用法: ./scripts/deploy_blog.sh <command>

命令:
  install     部署 web-blog 并启动 systemd 服务
  status      查看 ops-blog 服务状态
  logs        查看 ops-blog 最近日志
  uninstall   移除 systemd 服务（不删除 /opt/ops-blog 文件）
  help        显示帮助

环境变量:
  DEPLOY_DIR      默认 /opt/ops-blog
  SERVICE_NAME    默认 ops-blog
  PORT            默认 80

示例:
  sudo ./scripts/deploy_blog.sh install
  ./scripts/deploy_blog.sh status
  ./scripts/deploy_blog.sh logs
EOF
}

main() {
    local command="${1:-help}"
    case "${command}" in
        install) install_blog ;;
        status) status_blog ;;
        logs) logs_blog ;;
        uninstall) uninstall_blog ;;
        help|--help|-h) show_help ;;
        *)
            print_error "未知命令: ${command}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
