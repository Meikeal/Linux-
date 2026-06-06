# Meikeal Ops Blog

这是用于课程项目演示的个人 Web 博客站点。项目场景来自个人 Web 开发：

1. 平时开发博客或小型 Web 项目。
2. 将站点部署到 Linux 服务器。
3. 使用 `ops-assist` 对部署后的服务器进行巡检。

## 本地预览

```bash
cd web-blog
python3 -m http.server 8080
```

访问：

- 首页：`http://127.0.0.1:8080/`
- 健康检查：`http://127.0.0.1:8080/healthz.txt`

## Linux 部署

在服务器项目根目录运行：

```bash
sudo ./scripts/deploy_blog.sh install
```

部署后检查：

```bash
systemctl status ops-blog
curl http://127.0.0.1:8080/healthz.txt
./ops-assist all
```

`ops-assist` 默认会关注：

- `ops-blog` 服务状态
- `8080` 端口监听状态
- `http://127.0.0.1:8080/healthz.txt` 健康检查
