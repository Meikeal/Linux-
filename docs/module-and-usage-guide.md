# ops-assist 模块功能与运行说明

## 1. 项目定位

ops-assist 是一个 Linux 运维智能巡检与日志诊断助手。它面向个人 Web 开发和服务器部署场景：博客或 Web Demo 上线后，通过一条命令检查服务器资源、关键服务、端口、健康接口和系统日志，并生成可读报告。

本项目的真实部署对象是个人技术博客 `Meikeal AI Notes`，部署在 CentOS 7.9 云服务器上，对外提供 HTTP 访问。

## 2. 主入口模块：ops-assist

文件：`ops-assist`

功能：

- 解析命令行参数。
- 加载 `config/ops-assist.conf` 配置。
- 分发 `check`、`log`、`diagnose`、`report`、`all`、`deploy-blog` 等子命令。
- 在 `all` 模式下串联完整流程：系统巡检 -> 日志分析 -> 诊断建议 -> 报告生成。

运行示例：

```bash
./ops-assist help
./ops-assist check
./ops-assist all
```

## 3. 系统巡检模块：modules/check_system.sh

功能：

- 系统基本信息：主机名、内核版本、系统版本、运行时间。
- CPU 状态：CPU 使用率、1 分钟负载、CPU 核心数。
- 内存状态：总内存、已用内存、可用内存、Swap。
- 磁盘状态：分区容量和 inode 使用率。
- 进程状态：进程总数、CPU/内存 TOP 5、僵尸进程。
- 端口状态：检查 `WATCH_PORTS` 中的端口是否监听。
- 服务状态：检查 `WATCH_SERVICES` 中的 systemd 服务是否运行。
- 网络状态：统计 TCP 连接状态。
- Web 健康检查：访问 `HEALTH_URLS` 并判断是否返回 `ok`。

实现方式：

- 使用 Bash 作为主实现语言，适合 Linux 系统管理课程要求。
- 调用 `uname`、`uptime`、`free`、`df`、`ps`、`ss/netstat`、`systemctl`、`curl/wget` 等 Linux 常用命令。
- 通过 `[OK]`、`[WARN]`、`[ERROR]` 标记每个检查项状态。

运行示例：

```bash
./ops-assist check
./ops-assist check logs/check_manual.log
```

## 4. 日志分析模块：modules/log_analyzer.sh

功能：

- 扫描系统日志或用户指定日志。
- 匹配异常关键词，例如 error、failed、denied、timeout、refused、panic 等。
- 输出异常行、上下文和统计信息。

实现方式：

- 使用 Bash 读取日志路径。
- 使用 `grep`、`awk`、`sed` 等命令进行关键词匹配和上下文提取。
- 支持通过 `-f` 指定日志文件，也支持默认扫描系统常见日志。

运行示例：

```bash
./ops-assist log
./ops-assist log -f /var/log/messages
```

## 5. 智能诊断模块：scripts/diagnose.py

功能：

- 读取巡检结果。
- 根据 `[WARN]`、`[ERROR]` 和关键词生成诊断建议。
- 将问题转换成更容易理解的运维建议。

实现方式：

- 使用 Python 对巡检日志进行文本解析。
- 按磁盘、内存、服务、端口、健康检查等类别输出建议。
- 适合把原始命令输出变成答辩时能解释的结论。

运行示例：

```bash
python3 scripts/diagnose.py --input logs/check_xxx.log --output logs/diagnose_xxx.txt
```

## 6. 报告生成模块：scripts/report.py

功能：

- 汇总系统巡检、日志分析和诊断建议。
- 生成 Markdown 或 HTML 报告。
- 新增“巡检项目说明表”，逐项解释检查内容、当前状态和结果含义。

实现方式：

- 使用 Python 解析巡检日志中的章节。
- 根据 `[OK]`、`[WARN]`、`[ERROR]` 判断每个检查项状态。
- 对每个检查项补充面向人的解释，解决原始日志过于简单的问题。

运行示例：

```bash
./ops-assist report --format markdown
./ops-assist report --format html
```

完整流程运行后，报告会自动生成在：

```bash
reports/
```

## 7. 博客部署模块：scripts/deploy_blog.sh

功能：

- 将 `web-blog/` 静态博客部署到 `/opt/ops-blog`。
- 安装 systemd 服务 `ops-blog`。
- 启动并设置开机自启。
- 提供 `install`、`status`、`restart`、`stop` 等管理操作。

实现方式：

- 使用 Bash 复制博客文件。
- 使用 Python 静态文件服务器提供 HTTP 服务。
- 使用 systemd 管理进程生命周期。

运行示例：

```bash
sudo ./ops-assist deploy-blog install
sudo ./ops-assist deploy-blog status
sudo ./ops-assist deploy-blog restart
```

## 8. 配置文件：config/ops-assist.conf

核心配置：

```bash
WATCH_SERVICES="sshd ops-blog"
WATCH_PORTS="22 80"
HEALTH_URLS="http://127.0.0.1/healthz.txt"
DISK_WARN_THRESHOLD=80
MEM_WARN_THRESHOLD=80
```

说明：

- `WATCH_SERVICES`：需要检查的 systemd 服务。
- `WATCH_PORTS`：需要确认监听的端口。
- `HEALTH_URLS`：Web 健康检查地址。
- `DISK_WARN_THRESHOLD`：磁盘告警阈值。
- `MEM_WARN_THRESHOLD`：内存告警阈值。

## 9. 推荐演示命令

```bash
cd /opt/ops-assist-project
curl http://127.0.0.1/healthz.txt
systemctl status ops-blog --no-pager
ss -tlnp | grep ':80'
./ops-assist all
ls -lh reports/
tail -n 60 reports/report_*.md
```

