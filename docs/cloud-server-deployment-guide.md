# 云服务器部署指南

本项目的答辩场景调整为：

> 我平时做 Web 开发，完成个人博客后部署到 Linux 云服务器；部署后使用 ops-assist 对服务器进行巡检，检查服务、端口、健康检查地址、日志和系统资源。

## 推荐服务器配置

博客是静态站点，资源需求很低：

- 系统：Ubuntu 22.04 LTS 或 Ubuntu 24.04 LTS
- CPU：1 核或 2 核即可
- 内存：1GB 以上即可，2GB 更稳
- 磁盘：20GB 以上
- 带宽：1Mbps 以上即可
- 必须有公网 IPv4

## 购买建议

### 方案 A：国内轻量应用服务器

适合课堂展示，控制台中文，购买和开放端口比较简单。

建议选择：

- 腾讯云轻量应用服务器
- 阿里云轻量应用服务器
- Ubuntu 镜像
- 地域选择离你近的国内地域

注意：

- 如果只用公网 IP + 端口访问，可以先不买域名。
- 如果要绑定域名并使用 80/443 长期公开访问，国内服务器通常需要备案。
- 8080 端口通常需要在云平台防火墙/安全组中手动放行。

### 方案 B：Oracle Cloud Always Free

适合省钱，但注册、开机容量和网络配置可能更折腾。

建议只在你愿意花时间处理账号注册、区域容量和安全列表规则时选择。

## 服务器创建后需要记录的信息

请把下面信息发给我，我就可以继续远程部署：

```text
公网 IP：
SSH 用户名：root 或 ubuntu
登录方式：密码 / 私钥
系统版本：Ubuntu 22.04 / Ubuntu 24.04 / 其他
是否已放行端口：22、8080、80、443
```

如果是私钥登录，请把私钥文件保存到本机，并告诉我路径。不要在聊天里直接粘贴私钥正文。

## 部署步骤

服务器可 SSH 登录后，在服务器上执行：

```bash
sudo apt update
sudo apt install -y git python3 curl
git clone https://github.com/Meikeal/Linux-.git
cd Linux-
sudo ./ops-assist deploy-blog install
curl http://127.0.0.1:8080/healthz.txt
./ops-assist all
```

公网访问：

```text
http://服务器公网IP:8080/
http://服务器公网IP:8080/healthz.txt
```

## 巡检验证

部署完成后执行：

```bash
./ops-assist check
./ops-assist log -f samples/sample_logs/syslog_sample.log
./ops-assist all
bash tests/test_workflow.sh
```

重点检查：

- `ops-blog` 服务是否运行
- `8080` 端口是否监听
- `healthz.txt` 是否返回 `ok`
- `reports/` 是否生成 Markdown 报告
- `tests/test_workflow.sh` 是否全部通过

## 常见问题

### 公网打不开

检查云平台防火墙/安全组是否放行 8080。

```bash
curl http://127.0.0.1:8080/healthz.txt
systemctl status ops-blog
ss -tlnp | grep 8080
```

### 服务启动失败

```bash
journalctl -u ops-blog -n 80 --no-pager
sudo systemctl restart ops-blog
```

### 想改成 80 端口

可以把 `PORT=80` 传给部署脚本，或后续配置 nginx 反向代理。

```bash
sudo PORT=80 ./ops-assist deploy-blog install
```
