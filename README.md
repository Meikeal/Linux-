# Linux 运维智能巡检与日志诊断助手

> 《Linux 系统管理与 Shell 编程》课程项目 | 版本 1.3.0

## 目录

- [项目简介](#项目简介)
- [项目背景与问题](#项目背景与问题)
- [快速开始](#快速开始)
- [功能模块](#功能模块)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [完整开发过程](#完整开发过程)
- [测试说明](#测试说明)
- [技术栈](#技术栈)
- [常见问题](#常见问题)
- [许可证](#许可证)

---

## 项目简介

**ops-assist** 是一个面向个人 Web 开发部署场景的命令行巡检与日志诊断工具。本项目同时包含一个可部署的动态博客 `web-blog`，用于模拟我平时完成 Web 项目后部署到 Linux 服务器的真实场景；部署后再由 ops-assist 对服务、端口、健康检查地址、系统资源和日志异常进行巡检。

### 项目目标

> 不是做大型平台，而是用 Linux 命令和 Shell 自动化解决一个可观察、可测试的实际运维问题。

---

## 项目背景与问题

### 服务对象

服务对象是我自己：平时做 Web 开发并把个人博客、小型页面或课程项目部署到 Linux 服务器的开发者。典型场景是：本地完成博客站点开发后，将站点部署为 Linux systemd 服务，再定期检查服务是否存活、端口是否监听、日志是否异常、磁盘和内存是否正常。

### 解决的实际问题

在日常 Linux 使用中，以下问题频繁出现却缺乏便捷的自动化排查手段：

| 问题 | 现有做法 | 痛点 |
|------|----------|------|
| 磁盘被日志/缓存占满 | 手动执行 `df -h`，逐目录排查 | 命令分散，容易遗漏 |
| 博客服务异常退出未被发现 | 偶尔检查 `systemctl status ops-blog` | 无法及时发现 |
| SSH 登录失败持续增加 | 偶尔查看 `/var/log/auth.log` | 缺乏统计和趋势分析 |
| Web 端口未监听或被占用 | 手动 `ss -tlnp` 逐端口检查 | 重复劳动 |
| 系统负载升高原因不明 | 分别执行 `top`、`free`、`ps` | 信息分散，关联困难 |

### 为什么需要本项目

Linux 原生命令虽然强大，但信息分散在不同命令中，输出格式不直观，缺少关联分析，无法自动化定时执行。对个人 Web 项目来说，部署完成不代表服务长期稳定，因此 **ops-assist** 将博客部署后的高频巡检操作串联为一条命令，自动标记异常、生成诊断建议、输出可存档的报告。

---

## 快速开始

### 环境要求

- **操作系统**: Linux (Ubuntu/Debian/CentOS/WSL 均可)
- **Shell**: Bash 4.0+
- **Python**: Python 3.6+
- **权限**: 读取系统日志需要 sudo（可选，可使用样例日志测试）

### 下载与安装

```bash
# 克隆仓库
git clone https://github.com/Meikeal/Linux-.git
cd Linux-

# 添加执行权限
chmod +x ops-assist
chmod +x modules/*.sh
chmod +x scripts/*.sh
chmod +x tests/*.sh
chmod +x scripts/*.py
```

### 三步验证

```bash
# Step 1: 查看帮助
./ops-assist help

# Step 2: 使用样例日志运行完整流程
./ops-assist all

# Step 3: 查看生成的报告
ls reports/
cat reports/report_*.md
```

### 博客部署演示

项目内置一个个人博客站点 `web-blog/`，可部署为 Linux 服务 `ops-blog`：

```bash
# 本地预览动态博客
python3 web-blog/server.py --host 127.0.0.1 --port 8080 --directory web-blog

# Linux 服务器部署（在项目根目录）
sudo ./ops-assist deploy-blog install

# 验证健康检查
curl http://127.0.0.1/healthz.txt

# 对部署后的博客服务器进行巡检
./ops-assist all
```

---

## 功能模块

### 1. 系统状态巡检 (`ops-assist check`)

自动采集 7 大类系统状态，异常项自动标记：

| 检查项 | 采集内容 | 使用命令 |
|--------|----------|----------|
| 系统基本信息 | 主机名、内核版本、运行时间 | `hostname`, `uname`, `uptime` |
| CPU 状态 | 使用率、系统负载、核心数 | `mpstat`, `top`, `nproc` |
| 内存状态 | 内存/Swap 使用率 | `free` |
| 磁盘状态 | 分区使用率、Inode 使用率 | `df` |
| 进程状态 | CPU/内存 TOP5、僵尸进程 | `ps` |
| 端口状态 | 配置端口监听状态 | `ss`, `netstat` |
| 服务状态 | systemd 服务运行状态 | `systemctl` |
| Web 健康检查 | 博客健康检查 URL 是否可访问 | `curl`, `wget` |

### 2. 日志异常分析 (`ops-assist log`)

- 关键词过滤：`error`、`failed`、`denied`、`timeout`、`disconnect`、`refused`、`panic`、`OOM`、`segfault`
- 异常事件统计与排序（TOP 10）
- 时间分布分析（按小时）
- 特定模式检测：SSH 暴力破解、OOM 事件、磁盘 I/O 错误、服务崩溃
- 异常上下文提取

### 3. 诊断建议 (`ops-assist diagnose`)

基于规则引擎，根据巡检结果自动匹配诊断规则，覆盖 10+ 种常见异常场景，每种提供 4 条具体操作建议。

### 4. 报告生成 (`ops-assist report`)

将系统巡检结果、日志分析摘要、诊断建议汇总为 Markdown 或 HTML 报告，支持归档对比。

### 5. 定时巡检 (`scripts/setup_cron.sh`)

```bash
# 安装每日巡检（默认凌晨2点）
./scripts/setup_cron.sh install

# 安装每小时巡检
./scripts/setup_cron.sh install -i hourly

# 自定义 cron 表达式（每6小时）
./scripts/setup_cron.sh install -i custom -c "0 */6 * * *"

# 查看定时任务状态
./scripts/setup_cron.sh status

# 移除定时任务
./scripts/setup_cron.sh uninstall
```

### 6. 个人博客部署 (`ops-assist deploy-blog`)

将 `web-blog/` 部署到 Linux 服务器 `/opt/ops-blog`，安装为 `ops-blog` systemd 服务并监听 `80` 端口：

```bash
sudo ./ops-assist deploy-blog install
./ops-assist deploy-blog status
./ops-assist deploy-blog logs
```

部署后，巡检配置默认关注：

- `ops-blog` 服务状态
- `80` 端口监听状态
- `http://127.0.0.1/healthz.txt` 健康检查

---

## 项目结构

```
Linux-/
├── ops-assist                  # 主入口脚本（bash）— 命令解析与分发
├── modules/
│   ├── check_system.sh         # 系统状态巡检模块（~350行）
│   └── log_analyzer.sh         # 日志异常分析模块（~330行）
├── scripts/
│   ├── report.py               # 报告生成（Markdown/HTML）（~250行）
│   ├── diagnose.py             # 诊断建议生成（~240行）
│   ├── setup_cron.sh           # crontab 定时任务配置（~230行）
│   └── deploy_blog.sh          # 个人博客 Linux 部署脚本
├── config/
│   ├── ops-assist.conf         # 告警阈值与监控项配置
│   └── ops-blog.service        # 博客 systemd 服务模板
├── web-blog/                   # 可部署的个人动态博客站点
├── samples/
│   └── sample_logs/
│       ├── README.md           # 样例日志说明
│       └── syslog_sample.log   # 样例系统日志（49行，含多种异常）
├── tests/
│   └── test_workflow.sh        # 功能测试脚本（11项测试）
├── reports/                    # 巡检报告输出目录
├── logs/                       # 运行日志目录
├── CLAUDE.md                   # Agent 操作边界与项目规范
├── .gitignore
└── README.md                   # 本文件
```

### 代码统计

| 类别 | 文件数 | 代码行数 |
|------|--------|----------|
| Shell 脚本 | 5 | ~1,250 行 |
| Python 脚本 | 2 | ~490 行 |
| 配置/测试/文档 | 8 | ~200 行 |
| **合计** | **15** | **~1,940 行** |

---

## 配置说明

编辑 `config/ops-assist.conf` 调整参数：

```bash
# 磁盘使用率告警阈值
DISK_WARN_THRESHOLD=80      # 警告阈值（%）
DISK_CRITICAL_THRESHOLD=90  # 严重阈值（%）

# 内存使用率告警阈值
MEM_WARN_THRESHOLD=80
MEM_CRITICAL_THRESHOLD=90

# CPU 负载告警阈值
CPU_LOAD_WARN=2.0

# 需要监控的服务列表
WATCH_SERVICES="sshd ops-blog"

# 需要监控的端口列表
WATCH_PORTS="22 80"

# Web 健康检查地址
HEALTH_URLS="http://127.0.0.1/healthz.txt"

# 日志分析关键词（正则表达式）
LOG_PATTERNS="error|failed|denied|timeout|disconnect|refused|panic|OOM|segfault"

# 报告格式：markdown 或 html
REPORT_FORMAT="markdown"
```

---

## 使用指南

### 基本用法

```bash
# 系统巡检（输出到终端）
./ops-assist check

# 巡检结果保存到文件
./ops-assist check -o logs/check_result.log

# 分析指定日志
./ops-assist log -f /var/log/syslog

# 分析样例日志（无需 sudo）
./ops-assist log -f samples/sample_logs/syslog_sample.log

# 生成诊断建议
./ops-assist diagnose -i logs/check_result.log

# 生成 HTML 报告
./ops-assist report -i logs/check.log logs/analysis.log logs/diagnose.txt \
    --format html -o reports/inspection.html

# 一键完整巡检
./ops-assist all
```

### 权限说明

| 场景 | 所需权限 | 说明 |
|------|----------|------|
| 基础巡检（CPU/内存/磁盘） | 普通用户 | 无需特殊权限 |
| 读取系统日志 | sudo 或 adm 组 | `/var/log/syslog` 等文件 |
| 查看服务状态 | 普通用户 | `systemctl` 只读权限 |
| 安装定时任务 | 普通用户 | `crontab` 用户级 |
| 使用样例日志测试 | 普通用户 | 无需任何特殊权限 |

### 典型工作流

```bash
# 1. 先用样例日志验证功能正常
./ops-assist all

# 2. 检查生成的报告
cat reports/report_*.md

# 3. 配置定时任务（可选）
./scripts/setup_cron.sh install

# 4. 查看定时任务状态
./scripts/setup_cron.sh status

# 5. 分析真实系统日志（需要 sudo）
sudo ./ops-assist log -f /var/log/syslog
```

---

## 完整开发过程

项目采用迭代开发模式，从 V0.1 到 V1.0 共经历 **6 个版本、8 次提交**，每个版本聚焦一个核心功能模块。

### 版本迭代总览

```
V0.1 (项目框架) ──► V0.2 (系统巡检) ──► V0.3 (日志分析) ──► V0.4 (诊断报告) ──► V0.5 (定时集成) ──► V1.0 (正式发布)
```

### V0.1 — 项目基础框架（2026-05-13）

**提交**: `3f1ae5f`

**完成内容**:
- 创建项目目录结构（modules/、scripts/、config/、samples/、tests/）
- 实现 `ops-assist` 主入口脚本：参数解析、子命令分发（check/log/diagnose/report/all/help）
- 添加配置文件 `ops-assist.conf`：告警阈值、监控服务列表、端口列表、日志关键词
- 添加各模块占位文件

**测试重点**: `./ops-assist help` 和 `./ops-assist version` 能正确输出

### V0.2 — 系统状态巡检模块（2026-05-13）

**提交**: `961420c`

**完成内容**:
- 实现 `check_system.sh`：7 大检查项（系统信息、CPU、内存、磁盘、进程、端口、服务）
- 可配置告警阈值（磁盘/内存/CPU负载）
- 自动识别可用命令并降级处理（ss/netstat/free/mpstat 等）
- 异常标记：`[OK]` / `[WARN]` / `[ERROR]` 分级输出

**测试重点**: 各检查项数据采集是否准确，告警阈值是否触发

### V0.3 — 日志异常分析模块（2026-05-13）

**提交**: `d1c8d32` → `705b73a`（含样例日志补充）

**完成内容**:
- 实现 `log_analyzer.sh`：关键词过滤、高频错误 TOP10、时间分布、特定模式检测
- 添加样例日志 `syslog_sample.log`（49行，覆盖 SSH 暴力破解、OOM、磁盘错误、服务崩溃等场景）
- 使用 `grep/sed/awk` 进行文本处理

**测试重点**: 样例日志关键词统计是否正确，异常检测是否准确

### V0.4 — 诊断建议与报告生成（2026-05-13）

**提交**: `a2c9ae0`

**完成内容**:
- 实现 `diagnose.py`：基于规则的诊断建议引擎，覆盖磁盘/内存/CPU/OOM/SSH/磁盘错误/服务异常/端口异常/僵尸进程等场景
- 实现 `report.py`：支持 Markdown 和 HTML 格式报告，汇总巡检+日志+诊断结果
- 添加 `test_workflow.sh` 测试脚本（11项测试）
- 修复 Python 解释器自动检测

**测试重点**: 完整流程能否串联运行，报告内容是否完整

### V0.5 — Crontab 定时巡检与集成联调（2026-05-13）

**提交**: `8e76768`

**完成内容**:
- 实现 `setup_cron.sh`：支持 install/uninstall/show/status，支持 hourly/daily/12h/custom 多种间隔
- 修复 `grep -c` 与 `pipefail` 兼容性问题（无匹配时返回 `0\n0` 的 bug）
- 修复子模块非零返回值导致 `ops-assist all` 中断的问题
- 完成完整巡检流程联调

**发现与修复**:
| 问题 | 原因 | 修复方式 |
|------|------|----------|
| `grep -c` 输出 `0\n0` | `set -o pipefail` 下 grep 无匹配返回1，`\|\| echo 0` 追加了第二个0 | 改为 `(grep -c ... \|\| true) \| head -1` |
| `ops-assist all` 中途退出 | 子脚本返回非零值触发 `set -e` | 在分发函数中添加 `\|\| true` |
| `python3` 命令不可执行 | Windows 环境 `python3` 存在但无法运行 | 改为实际运行测试检测 |

### V1.0 — 整体联调与正式发布（2026-05-13）

**提交**: `5ab1752`

**完成内容**:
- 版本号升级至 1.3.0
- 功能测试 11/11 全部通过
- 添加 README.md
- 最终验证：`ops-assist all` 全流程正常运行

---

## 测试说明

### 运行测试

```bash
# 运行功能测试套件
./tests/test_workflow.sh
```

### 测试覆盖

| 测试项 | 内容 |
|--------|------|
| 模块存在性 | 主脚本、4个功能模块文件均存在且可执行 |
| 基础命令 | help 和 version 命令正常输出 |
| 巡检模块 | 能正常运行并生成输出文件 |
| 日志分析 | 能用样例日志完成分析并输出结果 |
| 诊断建议 | 能读取巡检结果并生成诊断报告 |
| 报告生成 | 能汇总三个输入源生成完整报告 |

### 异常测试建议

在实际 Linux 环境中建议额外测试：

```bash
# 权限不足场景（无 sudo 分析系统日志）
./ops-assist log -f /var/log/syslog

# 服务不存在场景
# 在配置中将不存在的服务加入 WATCH_SERVICES，观察输出

# 日志文件不存在场景
./ops-assist log -f /nonexistent/file.log
```

---

## 技术栈

本项目使用了《Linux 系统管理与 Shell 编程》课程中的 **8 项核心技术**：

| 技术 | 应用位置 |
|------|----------|
| Shell 脚本（bash） | `ops-assist`、`check_system.sh`、`log_analyzer.sh`、`setup_cron.sh` |
| Linux 系统命令 | `df`、`free`、`ps`、`ss`、`systemctl`、`uptime`、`hostname` 等 |
| grep/sed/awk 文本处理 | `log_analyzer.sh` 日志过滤、字段提取、异常统计 |
| 管道与重定向 | 命令组合、中间结果保存、报告文件输出 |
| 文件与权限管理 | 目录创建（reports/logs）、日志读取权限检查 |
| crontab 定时任务 | `setup_cron.sh` 无人值守巡检 |
| Python 调用 Linux 功能 | `report.py`、`diagnose.py` 结果处理与报告生成 |
| Git 代码管理 | 8 次提交，6 个版本标签，完整迭代记录 |

---

## 常见问题

### Q: 运行 `./ops-assist check` 显示 "free 命令不可用"？

A: 部分精简 Linux 环境可能缺少 `free` 命令，安装 `procps` 包即可：`apt install procps`。脚本已做降级处理，不会因此崩溃。

### Q: 分析系统日志提示权限不足？

A: 使用 `sudo ./ops-assist log -f /var/log/syslog`，或使用内置样例日志测试：`./ops-assist log -f samples/sample_logs/syslog_sample.log`。

### Q: 定时任务没有执行？

A: 检查 crontab 是否安装成功：`./scripts/setup_cron.sh status`。查看运行日志：`cat logs/cron_run.log`。常见原因：cron 服务未启动、脚本路径错误。

### Q: 如何在 WSL 上使用？

A: 完全支持。在 WSL 终端中直接运行即可，日志分析功能建议使用样例日志测试。

### Q: "僵尸进程检测"在测试环境误报？

A: 沙箱环境中 `ps` 输出格式可能与标准 Linux 不同。在实际 Linux 环境中表现正常。

---

## 许可证

本项目为《Linux 系统管理与 Shell 编程》课程项目，仅用于学习和教育目的。

---

*最后更新: 2026-06-06 | ops-assist v1.3.0*
