#!/usr/bin/env python3
"""Dynamic blog server backed by SQLite.

The service intentionally stays dependency-free so it can run on a fresh
CentOS server with only Python 3 installed.
"""

import argparse
import hashlib
import json
import mimetypes
import multiprocessing
import os
import sqlite3
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import socketserver

STARTED_AT = time.time()
DB_PATH = None
ROOT_DIR = None

POSTS = [
    {
        "slug": "cnn-to-vit",
        "title": "从 CNN 到 Vision Transformer：图像模型的归纳偏置",
        "tag": "深度学习",
        "date": "2026-06-06",
        "summary": "CNN 把图像先验写进网络结构，ViT 则把图像切成 token 后交给自注意力学习全局关系。",
        "content": "CNN 的局部连接、权值共享和平移等变性让模型更容易处理图像任务。Vision Transformer 的优势在于更灵活的全局建模，但通常需要更多数据和更强的训练策略。理解两者差异，有助于在小数据和大规模预训练场景中选择合适结构。",
    },
    {
        "slug": "overfitting-signals",
        "title": "训练模型时如何判断过拟合正在发生",
        "tag": "模型训练",
        "date": "2026-06-06",
        "summary": "当训练集损失继续下降而验证集损失上升时，模型可能正在记忆训练样本。",
        "content": "过拟合不是突然出现的，它通常会先体现在验证集曲线的拐点上。除了观察 loss，还可以检查错误样本、混淆矩阵和不同数据增强策略下的稳定性。常见缓解方式包括早停、权重衰减、dropout、数据增强和降低模型复杂度。",
    },
    {
        "slug": "pytorch-lr",
        "title": "PyTorch 实验记录：学习率为什么影响收敛速度",
        "tag": "PyTorch",
        "date": "2026-06-06",
        "summary": "学习率过小会让训练缓慢，过大则可能震荡甚至发散。",
        "content": "学习率是深度学习实验中最敏感的超参数之一。实际实验中可以先用较短训练轮次观察 loss 曲线，再配合 warmup、cosine decay 或 step decay 控制优化过程。对比不同学习率的曲线，比只看最终准确率更有解释力。",
    },
    {
        "slug": "ai-demo-deploy",
        "title": "把 AI Demo 部署到 Linux 服务器后的检查清单",
        "tag": "工程部署",
        "date": "2026-06-06",
        "summary": "模型 Demo 上线后，需要检查服务、端口、日志、资源和健康接口。",
        "content": "上线后的重点不只是页面能打开，还包括 systemd 服务是否 active、端口是否监听、磁盘和内存是否充足、日志中是否出现 failed 或 timeout。稳定的工程环境是模型结果可展示、可复现的基础。",
    },
]


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def dict_rows(cursor, rows):
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


def db_connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(root_dir):
    global DB_PATH
    data_dir = Path(root_dir) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    DB_PATH = data_dir / "ops_blog.db"

    with db_connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS posts (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                tag TEXT NOT NULL,
                date TEXT NOT NULL,
                summary TEXT NOT NULL,
                content TEXT NOT NULL,
                views INTEGER NOT NULL DEFAULT 0,
                likes INTEGER NOT NULL DEFAULT 0
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL,
                name TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                method TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS demo_load (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        for post in POSTS:
            conn.execute(
                """INSERT OR IGNORE INTO posts
                (slug, title, tag, date, summary, content)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    post["slug"],
                    post["title"],
                    post["tag"],
                    post["date"],
                    post["summary"],
                    post["content"],
                ),
            )
        conn.commit()


def now_text():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def clamp_int(value, default, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(max(number, minimum), maximum)


def memory_info_mb():
    total = 0
    available = 0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1]) // 1024
                elif line.startswith("MemAvailable:"):
                    available = int(line.split()[1]) // 1024
    except (OSError, ValueError):
        pass
    return total, available


def cpu_load_worker(seconds, duty_percent):
    deadline = time.time() + seconds
    window = 0.1
    busy_for = window * (duty_percent / 100.0)
    digest = b"ops-assist-cpu-load"
    loops = 0

    while time.time() < deadline:
        start = time.time()
        while time.time() - start < busy_for:
            digest = hashlib.sha256(digest + str(loops).encode("ascii")).digest()
            loops += 1
        rest = window - busy_for
        if rest > 0:
            time.sleep(rest)


def memory_load_worker(target_mb, seconds):
    chunks = []
    deadline = time.time() + seconds
    chunk_size = 1024 * 1024

    for _ in range(max(target_mb, 0)):
        block = bytearray(chunk_size)
        block[0] = 1
        block[-1] = 1
        chunks.append(block)

    while time.time() < deadline:
        for block in chunks[::128] or chunks[:1]:
            block[0] = (block[0] + 1) % 255
        time.sleep(0.5)


class BlogHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.client_address[0], fmt % args), flush=True)

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, status=HTTPStatus.OK):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, rel_path):
        safe = Path(rel_path.lstrip("/")).as_posix()
        file_path = (ROOT_DIR / safe).resolve()
        if not str(file_path).startswith(str(ROOT_DIR.resolve())) or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        data = file_path.read_bytes()
        content_type, _ = mimetypes.guess_type(str(file_path))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def record_metric(self, path, method, duration_ms):
        try:
            with db_connect() as conn:
                conn.execute(
                    "INSERT INTO metrics(path, method, duration_ms, created_at) VALUES (?, ?, ?, ?)",
                    (path[:120], method, duration_ms, now_text()),
                )
                conn.commit()
        except sqlite3.Error:
            pass

    def do_GET(self):
        started = time.time()
        try:
            self.handle_get()
        finally:
            self.record_metric(self.path, "GET", (time.time() - started) * 1000)

    def do_POST(self):
        started = time.time()
        try:
            self.handle_post()
        finally:
            self.record_metric(self.path, "POST", (time.time() - started) * 1000)

    def handle_get(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/healthz.txt":
            self.send_text("ok\n")
        elif path in ("/", "/index.html"):
            self.send_static("index.html")
        elif path == "/api/posts":
            self.api_posts()
        elif path.startswith("/api/posts/") and path.endswith("/comments"):
            slug = path.split("/")[3]
            self.api_comments(slug)
        elif path.startswith("/api/posts/"):
            slug = path.split("/")[3]
            self.api_post_detail(slug)
        elif path == "/api/search":
            self.api_search(query.get("q", [""])[0])
        elif path == "/api/stats":
            self.api_stats()
        elif path == "/api/demo-load":
            self.api_demo_load(query)
        elif path.startswith("/assets/"):
            self.send_static(path)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def handle_post(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/posts/") and path.endswith("/like"):
            slug = path.split("/")[3]
            self.api_like(slug)
        elif path.startswith("/api/posts/") and path.endswith("/comments"):
            slug = path.split("/")[3]
            self.api_add_comment(slug)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def api_posts(self):
        with db_connect() as conn:
            cur = conn.execute(
                """SELECT p.slug, p.title, p.tag, p.date, p.summary, p.views, p.likes,
                COUNT(c.id) AS comments
                FROM posts p LEFT JOIN comments c ON p.slug = c.slug
                GROUP BY p.slug
                ORDER BY p.date DESC, p.slug"""
            )
            self.send_json({"posts": [dict(row) for row in cur.fetchall()]})

    def api_post_detail(self, slug):
        with db_connect() as conn:
            conn.execute("UPDATE posts SET views = views + 1 WHERE slug = ?", (slug,))
            cur = conn.execute("SELECT * FROM posts WHERE slug = ?", (slug,))
            row = cur.fetchone()
            conn.commit()
        if not row:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_json({"post": dict(row)})

    def api_comments(self, slug):
        with db_connect() as conn:
            cur = conn.execute(
                "SELECT id, name, message, created_at FROM comments WHERE slug = ? ORDER BY id DESC LIMIT 20",
                (slug,),
            )
            self.send_json({"comments": [dict(row) for row in cur.fetchall()]})

    def api_add_comment(self, slug):
        data = self.read_json()
        name = str(data.get("name") or "访客").strip()[:24]
        message = str(data.get("message") or "").strip()[:300]
        if not message:
            self.send_json({"error": "comment message is required"}, HTTPStatus.BAD_REQUEST)
            return
        with db_connect() as conn:
            conn.execute(
                "INSERT INTO comments(slug, name, message, created_at) VALUES (?, ?, ?, ?)",
                (slug, name, message, now_text()),
            )
            conn.commit()
        self.send_json({"ok": True})

    def api_like(self, slug):
        with db_connect() as conn:
            conn.execute("UPDATE posts SET likes = likes + 1 WHERE slug = ?", (slug,))
            cur = conn.execute("SELECT likes FROM posts WHERE slug = ?", (slug,))
            row = cur.fetchone()
            conn.commit()
        if not row:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_json({"likes": row["likes"]})

    def api_search(self, term):
        keyword = "%" + term.strip()[:80] + "%"
        with db_connect() as conn:
            cur = conn.execute(
                """SELECT slug, title, tag, date, summary, views, likes
                FROM posts
                WHERE title LIKE ? OR tag LIKE ? OR summary LIKE ? OR content LIKE ?
                ORDER BY views DESC, date DESC""",
                (keyword, keyword, keyword, keyword),
            )
            self.send_json({"posts": [dict(row) for row in cur.fetchall()]})

    def api_stats(self):
        with db_connect() as conn:
            stats = {
                "posts": conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0],
                "comments": conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0],
                "views": conn.execute("SELECT COALESCE(SUM(views), 0) FROM posts").fetchone()[0],
                "likes": conn.execute("SELECT COALESCE(SUM(likes), 0) FROM posts").fetchone()[0],
                "requests": conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0],
                "avg_ms": round(conn.execute("SELECT COALESCE(AVG(duration_ms), 0) FROM metrics").fetchone()[0], 2),
                "uptime_seconds": int(time.time() - STARTED_AT),
                "db_kb": round(DB_PATH.stat().st_size / 1024, 1) if DB_PATH.exists() else 0,
            }
        self.send_json(stats)

    def api_demo_load(self, query):
        if self.client_address[0] not in ("127.0.0.1", "::1"):
            self.send_json({"error": "demo load is only available from localhost"}, HTTPStatus.FORBIDDEN)
            return

        seconds = clamp_int(query.get("seconds", ["30"])[0], 30, 1, 180)
        cpu_target = clamp_int(query.get("cpu", ["70"])[0], 70, 0, 95)
        memory_target = clamp_int(query.get("memory", ["0"])[0], 0, 0, 80)
        writes = clamp_int(query.get("writes", ["3000"])[0], 3000, 100, 50000)

        cpu_count = os.cpu_count() or 1
        total_mb, available_mb = memory_info_mb()
        used_mb = max(total_mb - available_mb, 0) if total_mb and available_mb else 0
        desired_used_mb = int(total_mb * memory_target / 100) if total_mb else 0
        memory_alloc_mb = max(desired_used_mb - used_mb, 0)
        if memory_target:
            memory_alloc_mb = min(memory_alloc_mb, max(int(total_mb * 0.75), 256))

        workers = []
        for _ in range(cpu_count if cpu_target else 0):
            proc = multiprocessing.Process(target=cpu_load_worker, args=(seconds, cpu_target))
            proc.start()
            workers.append(proc)

        memory_proc = None
        if memory_alloc_mb > 0:
            memory_proc = multiprocessing.Process(target=memory_load_worker, args=(memory_alloc_mb, seconds))
            memory_proc.start()
            workers.append(memory_proc)

        digest = b"ops-assist-demo-load"
        with db_connect() as conn:
            for i in range(writes):
                digest = hashlib.sha256(digest + str(i).encode("ascii")).digest()
                payload = hashlib.sha256(digest).hexdigest()
                conn.execute(
                    "INSERT INTO demo_load(payload, created_at) VALUES (?, ?)",
                    (payload, now_text()),
                )
            conn.commit()

        for proc in workers:
            proc.join()

        self.send_json(
            {
                "ok": True,
                "seconds": seconds,
                "cpu_target_percent": cpu_target,
                "cpu_workers": cpu_count if cpu_target else 0,
                "memory_target_percent": memory_target,
                "memory_alloc_mb": memory_alloc_mb,
                "memory_total_mb": total_mb,
                "memory_used_before_mb": used_mb,
                "db_writes": writes,
                "message": "目标资源演示负载已完成。演示时建议把 curl 放到后台运行，再立即执行 ./ops-assist check 或 ./ops-assist all。",
            }
        )


def main():
    parser = argparse.ArgumentParser(description="Serve the dynamic ops blog")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=80)
    parser.add_argument("--directory", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    global ROOT_DIR
    ROOT_DIR = Path(args.directory).resolve()
    init_db(ROOT_DIR)

    with ThreadedTCPServer((args.host, args.port), BlogHandler) as server:
        print("Serving dynamic blog {} on {}:{}".format(ROOT_DIR, args.host, args.port), flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
