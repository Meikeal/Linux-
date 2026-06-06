#!/bin/bash
# =============================================================================
# test_workflow.sh - 基本功能测试脚本
# 测试巡检系统的核心流程
# =============================================================================

PASSED=0
FAILED=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log_test() {
    local name="$1"
    local result="$2"
    if [[ "${result}" == "PASS" ]]; then
        echo "  [PASS] ${name}"
        PASSED=$((PASSED + 1))
    else
        echo "  [FAIL] ${name} - ${result}"
        FAILED=$((FAILED + 1))
    fi
}

echo "========================================="
echo "  ops-assist 功能测试"
echo "========================================="
echo ""

# 测试 1: 主脚本存在且可执行
if [[ -x "${SCRIPT_DIR}/ops-assist" ]]; then
    log_test "主脚本 ops-assist 存在且可执行" "PASS"
else
    log_test "主脚本 ops-assist 存在且可执行" "FAIL: 文件不存在或不可执行"
fi

# 测试 2: help 命令
if bash "${SCRIPT_DIR}/ops-assist" help > /dev/null 2>&1; then
    log_test "help 命令正常返回" "PASS"
else
    log_test "help 命令正常返回" "FAIL: 执行 help 命令失败"
fi

# 测试 3: version 命令
version_output=$(bash "${SCRIPT_DIR}/ops-assist" version 2>&1)
if echo "${version_output}" | grep -q "ops-assist"; then
    log_test "version 命令输出正确" "PASS"
else
    log_test "version 命令输出正确" "FAIL: 输出内容不正确"
fi

# 测试 4: 巡检模块存在
if [[ -f "${SCRIPT_DIR}/modules/check_system.sh" ]]; then
    log_test "系统巡检模块存在" "PASS"
else
    log_test "系统巡检模块存在" "FAIL: 文件不存在"
fi

# 测试 5: 日志分析模块存在
if [[ -f "${SCRIPT_DIR}/modules/log_analyzer.sh" ]]; then
    log_test "日志分析模块存在" "PASS"
else
    log_test "日志分析模块存在" "FAIL: 文件不存在"
fi

# 测试 6: 诊断建议模块存在
if [[ -f "${SCRIPT_DIR}/scripts/diagnose.py" ]]; then
    log_test "诊断建议模块存在" "PASS"
else
    log_test "诊断建议模块存在" "FAIL: 文件不存在"
fi

# 测试 7: 报告生成模块存在
if [[ -f "${SCRIPT_DIR}/scripts/report.py" ]]; then
    log_test "报告生成模块存在" "PASS"
else
    log_test "报告生成模块存在" "FAIL: 文件不存在"
fi

# 测试 8: 系统巡检运行测试
bash "${SCRIPT_DIR}/modules/check_system.sh" /tmp/test_ops_check.log > /dev/null 2>&1 || true
if [[ -s /tmp/test_ops_check.log ]] && grep -q "系统状态巡检报告" /tmp/test_ops_check.log; then
    log_test "系统巡检模块可运行" "PASS"
else
    log_test "系统巡检模块可运行" "FAIL: 输出文件未生成或内容异常"
fi

# 测试 9: 日志分析运行测试（使用样例日志）
sample_log="${SCRIPT_DIR}/samples/sample_logs/syslog_sample.log"
if [[ -f "${sample_log}" ]]; then
    bash "${SCRIPT_DIR}/modules/log_analyzer.sh" /tmp/test_ops_log.log -f "${sample_log}" > /dev/null 2>&1 || true
    if [[ -s /tmp/test_ops_log.log ]] && grep -q "日志异常分析报告" /tmp/test_ops_log.log; then
        log_test "日志分析模块可运行" "PASS"
    else
        log_test "日志分析模块可运行" "FAIL: 输出文件未生成或内容异常"
    fi
else
    log_test "日志分析模块可运行" "SKIP: 样例日志不存在"
fi

# 测试 10: 诊断建议运行测试
if [[ -f /tmp/test_ops_check.log ]]; then
    python "${SCRIPT_DIR}/scripts/diagnose.py" --input /tmp/test_ops_check.log --output /tmp/test_ops_diag.md > /dev/null 2>&1 || true
    if [[ -s /tmp/test_ops_diag.md ]] && grep -q "诊断建议报告" /tmp/test_ops_diag.md; then
        log_test "诊断建议模块可运行" "PASS"
    else
        log_test "诊断建议模块可运行" "FAIL: 输出文件未生成或内容异常"
    fi
else
    log_test "诊断建议模块可运行" "SKIP: 缺少巡检结果"
fi

# 测试 11: 报告生成运行测试
if [[ -f /tmp/test_ops_check.log && -f /tmp/test_ops_log.log && -f /tmp/test_ops_diag.md ]]; then
    python "${SCRIPT_DIR}/scripts/report.py" -i /tmp/test_ops_check.log /tmp/test_ops_log.log /tmp/test_ops_diag.md -o /tmp/test_ops_report.md > /dev/null 2>&1 || true
    if [[ -s /tmp/test_ops_report.md ]] && grep -q "Linux 运维智能巡检报告" /tmp/test_ops_report.md; then
        log_test "报告生成模块可运行" "PASS"
    else
        log_test "报告生成模块可运行" "FAIL: 输出文件未生成或内容异常"
    fi
else
    log_test "报告生成模块可运行" "SKIP: 缺少前置模块输出"
fi

# 清理
rm -f /tmp/test_ops_*.log /tmp/test_ops_*.md

echo ""
echo "========================================="
echo "  测试结果: ${PASSED} 通过, ${FAILED} 失败"
echo "========================================="

if [[ ${FAILED} -gt 0 ]]; then
    exit 1
fi
exit 0
