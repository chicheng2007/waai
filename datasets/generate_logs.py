# -*- coding: utf-8 -*-
"""
日志数据生成器 —— 生成 250 份用于练习的 Web 访问日志。

运行方式：PyCharm 里右键 Run，或命令行 python generate_logs.py
生成结果：在 access-logs/ 目录下生成 access_001.log ~ access_250.log

这份脚本本身就是很好的练习材料：它用到了 for / 列表 / 字典 / f-string / random，
正好是《SYNTAX-BOOTCAMP.md 语法急救包》里讲的几个零件。

注意：所有数据都是模拟的，IP 也是随意编的，仅用于学习分析，不对应真实攻击。
"""

import os
import random

random.seed(42)  # 固定种子：每次生成的"随机"结果都一样，方便复现和对照答案

OUT_DIR = os.path.join(os.path.dirname(__file__), "access-logs")

# ---------- 素材库 ----------

# 正常访客 IP（内网 + 一些公网）
NORMAL_IPS = [
    "192.168.1.100", "192.168.1.101", "192.168.1.102", "10.0.0.5", "10.0.0.8",
    "172.16.0.23", "203.0.113.7", "198.51.100.12", "192.0.2.45", "116.25.180.33",
]

# 恶意 IP（练习目标：能从日志里把它们揪出来）
ATTACK_IPS = [
    "45.33.22.11",     # 大量扫描 /admin、/wp-login.php
    "185.220.101.45",  # SQL 注入
    "91.240.118.172",  # 暴力破解登录
    "103.76.50.180",   # 探测敏感文件
]

# 正常访问路径
NORMAL_PATHS = [
    "/", "/index.html", "/about.html", "/products.html", "/news/tech",
    "/static/css/style.css", "/static/js/app.js", "/images/logo.png",
    "/api/v1/users", "/api/v1/status", "/contact", "/robots.txt",
]

# 攻击探测路径（high-signal，看到就可疑）
ATTACK_PATHS = [
    "/admin", "/wp-login.php", "/wp-admin/", "/phpmyadmin/index.php",
    "/.git/config", "/.env", "/backup.sql", "/shell.php", "/config.php.bak",
]

# SQL 注入 payload
SQLI_PAYLOADS = [
    "/search?q=1%27%20OR%20%271%27%3D%271",
    "/product?id=1%20UNION%20SELECT%20username,password%20FROM%20users",
    "/login?user=admin%27--",
]

# 正常 User-Agent
NORMAL_UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/605.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Firefox/121.0",
]

# 攻击工具 UA（练习目标：User-Agent 也是线索）
ATTACK_UA = [
    "sqlmap/1.7", "nikto/2.1.6", "python-requests/2.31", "masscan/1.0",
]


def make_line(ip, path, status, size, ua, day, hour, minute, second):
    """生成一行 Apache combined 格式的日志"""
    date = f"25/Nov/2026:{hour:02d}:{minute:02d}:{second:02d} +0800"
    return f'{ip} - - [{date}] "{path}" {status} {size} "-" "{ua}"'


def gen_one_file(index):
    """生成第 index 份日志，返回所有行"""
    lines = []
    n = random.randint(40, 90)  # 每个文件 40~90 行

    for _ in range(n):
        day = random.randint(1, 25)
        hour, minute, second = random.randint(0, 23), random.randint(0, 59), random.randint(0, 59)

        # 按概率决定这行是正常还是哪种攻击
        roll = random.random()
        if roll < 0.62:
            # 正常访问
            ip = random.choice(NORMAL_IPS)
            path = random.choice(NORMAL_PATHS)
            status = random.choice([200, 200, 200, 304, 301, 404])
            size = random.randint(200, 5000)
            ua = random.choice(NORMAL_UA)
        elif roll < 0.78:
            # 敏感路径扫描
            ip = random.choice([ATTACK_IPS[0], ATTACK_IPS[3]])
            path = random.choice(ATTACK_PATHS)
            status = random.choice([404, 403, 401])
            size = random.randint(100, 600)
            ua = random.choice(ATTACK_UA)
        elif roll < 0.90:
            # SQL 注入
            ip = ATTACK_IPS[1]
            path = random.choice(SQLI_PAYLOADS)
            status = random.choice([200, 500, 403])
            size = random.randint(300, 2000)
            ua = ATTACK_UA[0]
        else:
            # 暴力破解登录
            ip = ATTACK_IPS[2]
            path = "/login"
            status = 401  # 未授权，典型爆破特征
            size = random.randint(100, 300)
            ua = random.choice(ATTACK_UA)

        lines.append(make_line(ip, path, status, size, ua, day, hour, minute, second))

    lines.sort()  # 按时间字符串排序，看起来更像真实日志（时间顺序）
    return lines


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    total = 250
    for i in range(1, total + 1):
        lines = gen_one_file(i)
        path = os.path.join(OUT_DIR, f"access_{i:03d}.log")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print(f"已生成 {total} 个日志文件到：{OUT_DIR}")


if __name__ == "__main__":
    main()
