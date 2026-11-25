# 第 22 章 TCP/IP 与网络配置

## 本章目标

读完这一章，你将能够：

- 理解 TCP/IP 模型与各层协议（IP、TCP、UDP、ICMP、DNS、HTTP）
- 理解 IP 地址、子网掩码、网关、DNS
- 用命令行工具查看和配置网络接口
- 掌握网络诊断工具（ping、traceroute、ss、dig、curl）
- 理解端口与服务的对应关系
- 从安全视角理解网络

---

## 22.1 TCP/IP 模型基础

### 22.1.1 分层模型

TCP/IP 把网络通信分成几层，每层负责不同任务：

| 层 | 协议 | 负责什么 | 数据单位 |
|----|------|---------|---------|
| 应用层 | HTTP、DNS、SSH、FTP | 应用程序间通信 | 消息 |
| 传输层 | TCP、UDP | 端到端连接、可靠性 | 段/数据报 |
| 网络层 | IP、ICMP、路由 | 寻址和路由 | 包 |
| 链路层 | Ethernet、WiFi | 物理网络传输 | 帧 |

分层的好处：每层只关心自己的事。你写网页（应用层）时不用管数据怎么变成电信号（链路层）。

### 22.1.2 TCP vs UDP

| 特性 | TCP | UDP |
|------|-----|-----|
| 连接 | 面向连接（三次握手） | 无连接 |
| 可靠性 | 保证送达、有序 | 不保证 |
| 速度 | 较慢（有开销） | 快 |
| 应用 | HTTP、SSH、MySQL、邮件 | DNS、视频、游戏、DHCP |

TCP 像"打电话"（先接通、确认、有序对话），UDP 像"发短信"（发出去不管对方收没收到）。

### 22.1.3 三次握手（安全必知）

TCP 建立连接的三次握手：

```
客户端 → 服务端：SYN（我想连接）
服务端 → 客户端：SYN-ACK（好的，我也准备好了）
客户端 → 服务端：ACK（确认，开始通信）
```

这就是 `nmap` 端口扫描的基础——发 SYN 看对方是否回 SYN-ACK（端口开放）。SYN Flood 攻击就是发大量 SYN 不回 ACK，耗尽服务端资源（第 18 章的 syncookies 就是防这个）。

---

## 22.2 IP 地址与网络基础

### 22.2.1 IP 地址

IPv4 地址是 32 位，写成四段十进制（0-255），如 `192.168.1.10`。

私有 IP 范围（内网专用，不可在公网路由）：

| 范围 | 用途 |
|------|------|
| 10.0.0.0 – 10.255.255.255 | 大型网络 |
| 172.16.0.0 – 172.31.255.255 | 中型网络 |
| 192.168.0.0 – 192.168.255.255 | 小型网络/家用 |

回环地址 `127.0.0.1`（localhost）指向本机。

### 22.2.2 子网掩码

子网掩码用来区分"网络部分"和"主机部分"。如 `255.255.255.0`（/24）表示前 24 位是网络，后 8 位是主机。

`192.168.1.10/24` 表示这个 IP 在 `192.168.1.0/24` 网段，可容纳 254 个主机（1-254，0 是网络地址，255 是广播）。

### 22.2.3 网关与 DNS

- **网关（Gateway）**：离开本地网络、访问外网的"出口"路由器。
- **DNS**：把域名（如 `google.com`）解析成 IP 地址的系统。

---

## 22.3 查看网络配置

```bash
# 查看网络接口和 IP（推荐）
ip addr
ip a

# 查看路由表
ip route
ip route show

# 传统命令（需 net-tools）
ifconfig
route -n
```

`ip addr` 输出示例：

```bash
2: eth0: <BROADCAST,MULTICAST,UP> ...
    inet 192.168.1.10/24 brd 192.168.1.255 scope global eth0
```

说明网卡 eth0 的 IP 是 192.168.1.10，掩码 /24。

### 22.3.1 配置网络（了解）

现代系统用 NetworkManager 或 netplan：

```bash
# NetworkManager
nmcli device status
nmcli con show
sudo nmcli con mod "连接名" ipv4.addresses 192.168.1.20/24
sudo nmcli con up "连接名"

# netplan（Ubuntu Server，配置在 /etc/netplan/*.yaml）
sudo netplan apply
```

> **提示**：改网络配置要小心，尤其在远程连接时——改错会断连。云服务器改 IP/网关前要格外谨慎，最好通过控制台操作。

---

## 22.4 网络诊断工具

### 22.4.1 ping：测试连通性

```bash
ping -c 4 8.8.8.8         # 发 4 个包
ping -c 4 google.com
```

用 ICMP 协议测试目标是否可达、延迟多少、是否丢包。

### 22.4.2 traceroute：追踪路径

```bash
traceroute google.com
# 或
tracepath google.com
```

显示数据包经过的每一跳路由器，用于定位网络故障点。

### 22.4.3 ss / netstat：查看连接

```bash
ss -tuln              # 查看监听的 TCP/UDP 端口
ss -tunap             # 查看所有连接及对应进程
ss -lntp              # 监听的 TCP 端口 + 进程
```

> **安全必用**：`ss -tunap` 是排查异常连接的首选。看到陌生外联要警惕。

### 22.4.4 dig / nslookup：DNS 查询

```bash
dig google.com
dig @8.8.8.8 google.com       # 指定 DNS 服务器
dig -t MX example.com         # 查询邮件记录
nslookup google.com           # 简单版
```

### 22.4.5 curl / wget：HTTP 请求

```bash
curl -I https://example.com        # 只看响应头
curl -s https://api.example.com    # 静默获取内容
curl -X POST -d "data=1" url       # POST 请求
wget https://example.com/file.zip  # 下载文件
```

`curl` 是测试 Web 服务、调 API 的瑞士军刀。

---

## 22.5 端口与服务

### 22.5.1 知名端口

| 端口 | 服务 |
|------|------|
| 20/21 | FTP |
| 22 | SSH |
| 23 | Telnet（不安全） |
| 25 | SMTP |
| 53 | DNS |
| 80 | HTTP |
| 443 | HTTPS |
| 3306 | MySQL |
| 3389 | RDP |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 8080 | 常用 Web 备用端口 |

`/etc/services` 文件记录了端口与服务的映射：

```bash
grep "ssh\|http\|mysql" /etc/services
```

### 22.5.2 端口扫描原理（防守视角）

`nmap` 是端口扫描的标准工具：

```bash
nmap -sT 目标IP         # TCP 连接扫描
nmap -sS 目标IP         # SYN 半开扫描（需 root）
nmap -sV 目标IP         # 探测服务版本
nmap -p 1-1000 目标IP   # 指定端口范围
```

> ⚠️ **合规提醒**：**只扫描你自己的系统或获得授权的目标**。这里的讲解是为了让你理解攻击者如何探测，从而更好地防守（比如为什么第 18 章要关闭无用端口）。

### 22.5.3 防守视角

- 关闭无用端口（第 21 章服务最小化）
- 防火墙只开放必需端口（第 18 章）
- 用 `ss -tulnp` 定期检查 listening 端口
- 用 `nmap` 从外部扫描自己，验证暴露面

---

## 22.6 安全视角的网络配置

### 22.6.1 网络相关内核参数回顾

第 21 章讲的 sysctl 参数（rp_filter、syncookies、禁重定向）都是网络层加固。

### 22.6.2 hosts 文件

`/etc/hosts` 是本地静态 DNS 映射：

```bash
127.0.0.1 localhost
192.168.1.10 myserver
```

安全用途：可临时屏蔽恶意域名（把域名指向 127.0.0.1），但效果有限（攻击者可用 IP 直连）。

### 22.6.3 抓包分析

```bash
# tcpdump 抓包（需 root）
sudo tcpdump -i eth0
sudo tcpdump -i eth0 port 80
sudo tcpdump -i eth0 host 192.168.1.10
sudo tcpdump -w capture.pcap          # 保存到文件，用 Wireshark 分析
```

> **安全场景**：抓包能看到明文传输的密码（HTTP、FTP、Telnet）——这就是为什么要用 HTTPS/SSH 加密。在你自己的网络里抓包学习，能直观理解"为什么明文协议不安全"。

---

## 22.7 本章总结

| 知识点 | 内容 |
|--------|------|
| TCP/IP | 应用层/传输层/网络层/链路层；TCP 可靠、UDP 快 |
| 三次握手 | SYN → SYN-ACK → ACK；扫描和 SYN Flood 的基础 |
| IP 地址 | 私有范围 10./172.16-31./192.168.；回环 127.0.0.1 |
| 子网/网关/DNS | 掩码分网络主机部分；网关是出口；DNS 解析域名 |
| 查看配置 | `ip addr`、`ip route`、`ifconfig` |
| 诊断工具 | ping、traceroute、ss、dig、curl、wget |
| 端口服务 | `/etc/services`；22/80/443/3306 等知名端口 |
| 安全 | ss 查异常连接、nmap 自扫暴露面（仅授权）、tcpdump 抓包 |

---

## 本章练习

1. 用 `ip addr` 查看你的 IP 和子网掩码，判断所属网段。
2. 用 `ip route` 查看默认网关。
3. 用 `ping -c 4 8.8.8.8` 测试外网连通性。
4. 用 `ss -tuln` 查看本机监听端口，对照知名端口表识别服务。
5. 用 `dig google.com` 查看 DNS 解析结果。
6. 用 `curl -I https://www.baidu.com` 查看响应头。
7. 用 `grep -E "ssh|http|mysql" /etc/services` 查看端口映射。
8. （授权环境）用 `nmap -sT 127.0.0.1` 扫描本机，对比 `ss -tuln` 的结果。
9. 思考：TCP 三次握手为什么是端口扫描的基础？SYN Flood 攻击利用了握手的什么特性？

---

**下一章预告**：我们将学习常见网络服务——Web（Nginx/Apache）、DNS、DHCP 的搭建与安全配置。理解服务如何运行、如何加固。
