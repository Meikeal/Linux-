# 公网访问、健康检查与安装说明

## 1. 为什么巡检地址是 http://127.0.0.1/healthz.txt

`127.0.0.1` 是“当前这台机器自己”的回环地址。ops-assist 是部署在 Linux 云服务器上运行的，所以它访问 `http://127.0.0.1/healthz.txt` 时，访问的是云服务器自己提供的博客服务，而不是你电脑上的本地服务。

这样设计有两个好处：

- 可以绕过公网网络、浏览器缓存、安全组等外部因素，直接确认服务器本机的 Web 服务是否正常。
- 如果本机健康检查失败，说明服务进程、端口监听或本机网络就有问题；如果本机正常但公网不能访问，问题更可能在安全组、防火墙、公网 IP 或反向代理配置。

本项目中：

- ops-assist 在服务器上检查：`http://127.0.0.1/healthz.txt`
- 其他同学或老师访问博客：`http://115.29.184.235/`
- 其他人不需要下载任何东西，只需要用浏览器打开公网 IP。

`healthz.txt` 返回 `ok` 是故意设计成很短的机器可读响应。巡检程序只需要判断服务是否能快速返回健康状态，不需要在健康接口里返回完整网页内容。真正的页面内容在博客首页展示。

## 2. 其他人如何在自己的 Linux 系统安装助手

如果别人只是看博客，不需要安装助手。只有当别人也想在自己的 Linux 服务器上巡检时，才需要安装 ops-assist。

安装步骤：

```bash
git clone https://github.com/Meikeal/Linux-.git
cd Linux-
chmod +x ops-assist modules/*.sh scripts/*.sh scripts/*.py tests/*.sh
./ops-assist help
```

执行一次完整巡检：

```bash
./ops-assist all
```

如果要部署项目自带的博客服务：

```bash
sudo ./ops-assist deploy-blog install
```

查看服务：

```bash
systemctl status ops-blog
ss -tlnp | grep ':80'
curl http://127.0.0.1/healthz.txt
```

## 3. 如何改成巡检自己的服务

编辑配置文件：

```bash
vim config/ops-assist.conf
```

常用配置项：

```bash
WATCH_SERVICES="sshd ops-blog"
WATCH_PORTS="22 80"
HEALTH_URLS="http://127.0.0.1/healthz.txt"
```

例如别人部署的是 nginx，可以改成：

```bash
WATCH_SERVICES="sshd nginx"
WATCH_PORTS="22 80 443"
HEALTH_URLS="http://127.0.0.1/"
```

改完后运行：

```bash
./ops-assist all
```

报告会生成在 `reports/` 目录，日志会生成在 `logs/` 目录。

