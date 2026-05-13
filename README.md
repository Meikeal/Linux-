# Linux 运维智能巡检与日志诊断助手

《Linux 系统管理与 Shell 编程》课程项目

## 项目简介

命令行巡检与日志诊断工具，将系统状态采集、日志异常提取、诊断建议和报告生成串联起来，解决 Linux 环境下的日常运维问题。

## 快速开始

```bash
# 查看帮助
./ops-assist help

# 执行系统巡检
./ops-assist check

# 分析日志文件
./ops-assist log -f /var/log/syslog

# 执行完整巡检流程
./ops-assist all

# 安装定时巡检（每日）
./scripts/setup_cron.sh install
```

## 项目结构

```
├── ops-assist              # 主入口脚本
├── modules/
│   ├── check_system.sh     # 系统状态巡检
│   └── log_analyzer.sh     # 日志异常分析
├── scripts/
│   ├── report.py           # 报告生成 (Markdown/HTML)
│   ├── diagnose.py         # 诊断建议生成
│   └── setup_cron.sh       # 定时任务配置
├── config/
│   └── ops-assist.conf     # 配置文件
├── samples/
│   └── sample_logs/        # 样例日志
├── tests/
│   └── test_workflow.sh    # 功能测试
├── reports/                # 报告输出目录
└── logs/                   # 运行日志目录
```

## 功能模块

1. **系统状态巡检** — CPU/内存/磁盘/进程/端口/服务状态采集
2. **日志异常分析** — 关键词过滤、异常统计、模式检测
3. **诊断建议生成** — 基于规则的自动化诊断建议
4. **巡检报告生成** — Markdown/HTML 格式报告
5. **定时巡检** — crontab 无人值守自动巡检

## 使用技术

Shell 脚本、Linux 系统命令、grep/sed/awk、管道与重定向、文件与权限管理、crontab、Python、Git

## 版本历史

| 版本 | 内容 |
|------|------|
| v0.1 | 项目框架和主入口脚本 |
| v0.2 | 系统状态巡检模块 |
| v0.3 | 日志异常分析模块 |
| v0.4 | 诊断建议与报告生成 |
| v0.5 | crontab 定时巡检集成 |
| v1.0 | 整体联调与发布 |
