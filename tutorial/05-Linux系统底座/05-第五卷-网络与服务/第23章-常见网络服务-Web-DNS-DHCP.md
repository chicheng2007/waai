# 第 23 章 常见网络服务：Web / DNS / DHCP

## 本章目标

读完这一章，你将能够：

- 理解 C/S 模型与服务的运行方式
- 搭建并加固 Nginx Web 服务
- 理解 HTTPS/TLS 与证书
- 理解 DNS 服务原理与常见攻击（DNS 劫持、投毒）
- 理解 DHCP 服务原理与安全风险
- 掌握服务安全配置通用原则

---

## 23.1 服务运行模型

### 23.1.1 客户端/服务端（C/S）

网络服务遵循 C/S 模型：服务端监听端口等待请求，客户端发起请求，服务端响应。

```
客户端（浏览器）  →  请求  →  服务端（Nginx，监听 80/443）
客户端           ←  响应  ←  服务端
```

服务端通常是**守护进程（daemon）**，在后台持续运行。systemd 负责管理它们（第 25 章详解）。

### 23.1.2 服务安全通用原则

无论什么服务，安全配置都遵循：

1. **最小权限**：服务以非 root 用户运行
2. **只暴露必需**：只监听需要的地址和端口
3. **及时更新**：打补丁
4. **加固配置**：关闭不必要的功能、隐藏版本信息
5. **日志审计**：记录访问和错误日志
6. **资源限制**：防止 DoS（cgroup、超时设置）

---

## 23.2 Web 服务：Nginx

### 23.2.1 安装与基本操作

```bash
sudo apt install nginx
sudo systemctl start nginx
sudo systemctl enable nginx       # 开机自启
sudo systemctl status nginx
```

测试：浏览器访问 `http://localhost`，应看到 Nginx 欢迎页。

配置文件：

- 主配置：`/etc/nginx/nginx.conf`
- 站点配置：`/etc/nginx/sites-available/`（启用链接到 `sites-enabled/`）
- 默认站点根目录：`/var/www/html/`

### 23.2.2 配置示例

一个简单的站点配置：

```nginx
server {
    listen 80;
    server_name example.com;
    root /var/www/myapp;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

检查配置并重载：

```bash
sudo nginx -t                 # 检查语法
sudo systemctl reload nginx   # 平滑重载
```

### 23.2.3 Nginx 安全加固

```nginx
server {
    # 1. 隐藏版本号（减少信息泄露）
    server_tokens off;

    # 2. 限制请求大小和超时（防 DoS）
    client_max_body_size 10m;
    client_body_timeout 10s;
    keepalive_timeout 15s;

    # 3. 添加安全响应头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    # 4. 禁止访问隐藏文件
    location ~ /\. {
        deny all;
    }

    # 5. 限制 HTTP 方法
    if ($request_method !~ ^(GET|POST|HEAD)$) {
        return 405;
    }
}
```

> **信息泄露的危害**：默认 Nginx 会在响应头和错误页显示版本号（如 `nginx/1.18.0`）。攻击者据此能快速查找该版本的已知漏洞。隐藏版本是基本加固。

### 23.2.4 访问日志分析（呼应第 20 章）

```bash
# 日志格式在 nginx.conf 定义，默认 combined
tail -f /var/log/nginx/access.log

# 找出扫描行为
grep -E '\.\./|select|union|<script' /var/log/nginx/access.log

# 统计访问量 IP
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head
```

### 23.2.5 HTTPS / TLS

HTTPS = HTTP + TLS 加密，防止中间人窃听和篡改。

配置 HTTPS 需要证书（可用 Let's Encrypt 免费证书）：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
```

certbot 会自动申请证书、配置 Nginx、设置自动续期。

TLS 加固要点：

```nginx
ssl_protocols TLSv1.2 TLSv1.3;    # 禁用老的 SSLv3/TLSv1.0/1.1
ssl_prefer_server_ciphers on;
```

> **安全意义**：明文 HTTP 会被窃听（Wi-Fi 抓包就能看到密码），HTTPS 是Web 服务的标配。

---

## 23.3 DNS 服务

### 23.3.1 DNS 原理

DNS（域名系统）把域名解析成 IP。它是分布式、层级化的：

```
根域名服务器（.）
  → 顶级域服务器（.com）
    → 权威域名服务器（example.com）
      → 返回 IP
```

解析过程（递归查询）：本地缓存 → `/etc/hosts` → 本地 DNS → 根 → TLD → 权威。

### 23.3.2 DNS 记录类型

| 类型 | 作用 |
|------|------|
| A | 域名 → IPv4 地址 |
| AAAA | 域名 → IPv6 |
| CNAME | 别名 → 另一个域名 |
| MX | 邮件服务器 |
| NS | 域名服务器 |
| TXT | 文本（验证、SPF） |

### 23.3.3 查询工具

```bash
dig example.com A
dig example.com MX
dig @8.8.8.8 example.com      # 指定 DNS
nslookup example.com
host example.com
```

### 23.3.4 DNS 安全

常见攻击：

| 攻击 | 原理 | 防护 |
|------|------|------|
| DNS 劫持 | 篡改解析结果指向恶意 IP | DNSSEC、HTTPS |
| DNS 投毒 | 污染 DNS 缓存 | DNSSEC、随机源端口 |
| DNS 隧道 | 用 DNS 请求外传数据 | 监控异常 DNS 查询 |
| DDoS | 攻击 DNS 服务器 | 任播、限速 |

> **安全实践**：使用可信 DNS（如 8.8.8.8、1.1.1.1），重要服务启用 DNSSEC，监控异常 DNS 查询（DNS 隧道常用于数据外泄）。

---

## 23.4 DHCP 服务

### 23.4.1 DHCP 原理

DHCP（动态主机配置协议）自动给内网设备分配 IP、网关、DNS。工作流程（DORA）：

```
Discover（客户端广播找 DHCP 服务器）
Offer（服务器提供 IP）
Request（客户端请求该 IP）
Ack（服务器确认）
```

### 23.4.2 安全配置

```bash
sudo apt install isc-dhcp-server
```

配置文件 `/etc/dhcp/dhcpd.conf`：

```bash
default-lease-time 600;
max-lease-time 7200;
subnet 192.168.1.0 netmask 255.255.255.0 {
    range 192.168.1.100 192.168.1.200;
    option routers 192.168.1.1;
    option domain-name-servers 8.8.8.8;
}
```

### 23.4.3 DHCP 安全风险

| 风险 | 说明 | 防护 |
|------|------|------|
|  rogue DHCP | 攻击者私自开 DHCP 分配恶意网关（中间人） | DHCP Snooping（交换机） |
| IP 耗尽 | 耗尽地址池导致 DoS | 限制、监控 |
| 伪造响应 | 抢先响应客户端 | 端口安全、认证 |

> **安全场景**：内网中如果有人接入一个恶意 DHCP 服务器，把所有人的网关指向它，就能实施中间人攻击（窃听、篡改流量）。企业网络用 DHCP Snooping 防止。

---

## 23.5 综合：搭建一个安全的 Web 服务

检查清单：

```bash
# 1. 最小化安装，只装需要的东西
sudo apt install nginx

# 2. 服务以非 root 运行（Nginx 默认 worker 用 www-data）
ps aux | grep nginx

# 3. 隐藏版本、加安全头（见 23.2.3 配置）

# 4. 启用 HTTPS
sudo certbot --nginx -d yourdomain.com

# 5. 防火墙只开 80/443
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 6. 日志监控
sudo tail -f /var/log/nginx/access.log

# 7. 定期更新
sudo apt update && sudo apt upgrade

# 8. 用工具检查配置
sudo nginx -t
sudo lynis audit system
```

---

## 23.6 本章总结

| 知识点 | 内容 |
|--------|------|
| C/S 模型 | 服务端监听、客户端请求；守护进程后台运行 |
| 服务安全原则 | 最小权限、只暴露必需、更新、加固、日志、限资源 |
| Nginx | 安装、配置、隐藏版本、安全头、限制请求、禁隐藏文件 |
| HTTPS | HTTP + TLS；certbot 免费证书；禁老协议 |
| DNS | 层级解析；A/CNAME/MX/NS/TXT 记录；dig 查询 |
| DNS 安全 | 劫持、投毒、隧道、DDoS；DNSSEC |
| DHCP | DORA 流程；rogue DHCP 中间人风险；DHCP Snooping |

---

## 本章练习

1. 安装 Nginx，启动并访问 `http://localhost` 验证。
2. 用 `sudo nginx -t` 检查配置语法，用 `systemctl reload nginx` 重载。
3. 查看响应头 `curl -I http://localhost`，观察是否暴露版本号。
4. 给 Nginx 加上 23.2.3 的安全配置，重启后再看响应头变化。
5. 用 `dig example.com` 和 `dig example.com MX` 查看 DNS 解析。
6. 用 `awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn` 分析访问日志。
7. 思考：HTTPS 如何防止中间人窃听？为什么 Web 服务必须用 HTTPS？
8. 思考：rogue DHCP 攻击为什么能实施中间人攻击？DHCP Snooping 如何防护？

---

**下一章预告**：我们将学习 Docker 容器与容器安全——容器是现代 AI 部署和安全工具的主流形式，理解它的隔离机制和安全风险至关重要。
