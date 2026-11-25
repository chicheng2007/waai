# 第 30 章 Linux 安全工具链

## 本章目标

读完这一章，你将能够：

- 了解 Linux 安全工具的分类与生态
- 掌握常用信息收集、漏洞扫描、流量分析工具
- 掌握密码学工具与取证工具
- 搭建自己的安全实验室（靶场）
- 理解工具使用的合规边界
- 把前五卷知识整合到工具使用中

---

## 30.1 安全工具生态概览

Linux 是安全工具的"原住民平台"。工具按用途分类：

| 类别 | 代表工具 | 用途 |
|------|---------|------|
| 信息收集 | Nmap、Masscan、theHarvester | 发现主机、端口、服务 |
| 漏洞扫描 | OpenVAS、Nikto、sqlmap | 发现漏洞 |
| Web 安全 | Burp Suite、OWASP ZAP | Web 应用测试 |
| 流量分析 | Wireshark、tcpdump、Tshark | 抓包分析 |
| 密码学 | OpenSSL、GPG、hashcat、John | 加密、哈希、破解 |
|  forensic | Autopsy、Volatility | 取证 |
| 框架 | Metasploit、Kali Linux | 综合渗透平台 |
| 防御 | Snort/Suricata、OSSEC、fail2ban | 检测与防御 |

> ⚠️ **合规声明重申**：这些工具中很多是"双刃剑"。**只在自己的实验环境、授权靶场、获得书面授权的测试中练习**。未经授权使用属于违法行为。本教程只讲原理和防御视角。

---

## 30.2 信息收集工具

### 30.2.1 Nmap（端口/服务扫描）

```bash
sudo apt install nmap

nmap 目标IP                    # 基础扫描
nmap -sV 目标IP                # 探测服务版本
nmap -O 目标IP                 # 操作系统识别
nmap -A 目标IP                 # 全面扫描（激进）
nmap -p 1-1000 目标IP          # 指定端口
nmap -sS 目标IP                # SYN 扫描（需 root）
```

> **防御视角**：知道攻击者怎么扫，就知道为什么第 18/21 章要关端口、隐藏版本、用防火墙。用 `nmap` 扫自己，看暴露了什么。

### 30.2.2 其他

- **Masscan**：极快的端口扫描（全网段）
- **theHarvester**：收集邮箱、子域名、员工信息（OSINT）
- **dnsenum / dig**：DNS 信息收集

---

## 30.3 漏洞扫描工具

### 30.3.1 Nikto（Web 服务器扫描）

```bash
sudo apt install nikto
nikto -h http://目标
```

扫描 Web 服务器的危险文件、过时组件、配置问题。

### 30.3.2 sqlmap（SQL 注入检测）

```bash
sudo apt install sqlmap
sqlmap -u "http://目标/page?id=1" --batch
```

> **防御视角**：sqlmap 检测注入的原理，正是第 19 章 MySQL 卷讲的 SQL 注入。理解它才能写好防御（预编译语句、WAF 规则）。

### 30.3.3 OpenVAS / Greenbone

企业级的漏洞扫描器，功能全面，安装较复杂（GVM）。适合做定期漏洞评估。

---

## 30.4 流量分析工具

### 30.4.1 tcpdump（命令行抓包）

```bash
sudo tcpdump -i eth0
sudo tcpdump -i eth0 port 80
sudo tcpdump -i eth0 host 192.168.1.10
sudo tcpdump -w capture.pcap
sudo tcpdump -r capture.pcap
```

### 30.4.2 Wireshark / Tshark（图形/命令行分析）

```bash
sudo apt install wireshark tshark
tshark -r capture.pcap
```

Wireshark 能深入分析每个数据包的协议字段，是网络排查和安全分析的必备工具。

> **学习建议**：在自己网络里抓 HTTP 流量，能看到明文传输的用户名密码——直观理解"为什么必须 HTTPS"。

---

## 30.5 密码学工具

### 30.5.1 OpenSSL

```bash
# 生成私钥和自签名证书
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365

# 计算哈希
openssl dgst -sha256 file.txt

# Base64 编解码
echo "hello" | base64
echo "aGVsbG8=" | base64 -d
```

### 30.5.2 GPG（加密与签名）

```bash
gpg --gen-key                  # 生成密钥对
gpg --encrypt --recipient 邮箱 file.txt   # 加密
gpg --decrypt file.txt.gpg     # 解密
```

### 30.5.3 密码破解工具（仅授权环境）

- **John the Ripper**：离线密码哈希破解
- **hashcat**：高性能哈希破解（支持 GPU）

> **防御视角**：理解这些工具，才能明白"为什么密码要加盐、要用慢哈希（bcrypt/argon2）、要够长"。这是第 8、21 章密码策略的底层逻辑。

---

## 30.6 取证工具

### 30.6.1 Autopsy / The Sleuth Kit

磁盘取证工具，分析文件系统、恢复删除文件、时间线分析。

### 30.6.2 Volatility

内存取证框架，分析内存转储，找恶意进程、注入代码、网络连接。

```bash
volatility -f memory.dump imageinfo
volatility -f memory.dump --profile=Linux pslist
```

> **呼应第 20 章**：应急响应"先取证"时，内存取证能捕获磁盘上没有的证据（如内存中的恶意代码、加密密钥）。

---

## 30.7 防御工具

### 30.7.1 入侵检测

- **Snort / Suricata**：网络入侵检测系统（NIDS），基于规则检测攻击流量
- **OSSEC / Wazuh**：主机入侵检测（HIDS），第 20 章讲过

### 30.7.2 其他防御工具

- **fail2ban**：防暴力破解（第 19 章）
- **Lynis**：系统加固审计（第 21 章）
- **AIDE**：文件完整性（第 20 章）
- **Trivy**：容器/依赖漏洞扫描（第 24 章）

---

## 30.8 搭建安全实验室

### 30.8.1 推荐环境

搭建一个隔离的实验网络（虚拟机）：

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  攻击机       │     │  靶机         │     │  防御机       │
│  Kali Linux  │────▶│  DVWA/Vulhub │◀────│  Ubuntu+IDS  │
│  (安全工具)   │     │  (有漏洞应用) │     │  (检测防御)   │
└──────────────┘     └──────────────┘     └──────────────┘
         隔离的 Host-only / NAT 网络（不连公网）
```

### 30.8.2 靶场推荐

| 靶场 | 说明 |
|------|------|
| **DVWA** | Web 漏洞练习（SQL 注入、XSS 等），新手入门 |
| **Vulhub** | 一键搭建漏洞环境（Docker） |
| **HackTheBox / TryHackMe** | 在线渗透练习平台 |
| **CTF 题目** | 各类竞赛题目 |
| **自建漏洞应用** | 在自己的代码里故意留漏洞练习修复 |

### 30.8.3 隔离的重要性

- 实验网络用 **Host-only** 或 **NAT**，不要桥接到真实网络
- 不要在实验室里放真实敏感数据
- 靶机被打"脏"了就重建快照

> **再次强调**：所有练习必须在隔离的、自己完全控制的环境里。把工具指向公网他人系统是违法的。

---

## 30.9 工具使用的正确心态

1. **理解原理，而非只会敲命令**：知道 nmap 为什么能发现端口，sqlmap 为什么能注入，才能做好防御。
2. **防御者视角**：学攻击是为了更好地防守。始终问"这个攻击怎么检测、怎么防护"。
3. **合规第一**：授权、隔离、记录。
4. **持续学习**：安全工具和技术快速迭代，保持学习。

---

## 30.10 第六卷总结

| 章 | 核心内容 |
|----|---------|
| 26 | gcc/make/cmake/git；编译过程、构建工具、版本控制 |
| 27 | Python/C/Rust/Go on Linux；系统编程、语言选型、混合 |
| 28 | 性能分析四维度、USE 方法、perf/sar、调优循环 |
| 29 | GPU/CUDA/驱动、PyTorch GPU、nvidia-smi、容器 GPU |
| 30 | 安全工具链、靶场搭建、合规边界、防御者心态 |

> 第六卷把 Linux 变成你的开发、AI、安全主场。工具、语言、性能、GPU、安全生态——所有能力都在这里汇聚。

---

## 30.11 本章总结

| 知识点 | 内容 |
|--------|------|
| 工具分类 | 信息收集、漏洞扫描、Web、流量、密码、取证、防御 |
| Nmap | 端口/服务/OS 扫描；防御视角看暴露面 |
| Web 工具 | Nikto、sqlmap、Burp/ZAP（呼应 SQL 注入防御） |
| 流量 | tcpdump、Wireshark/Tshark |
| 密码 | OpenSSL、GPG、John/hashcat（理解密码策略） |
| 取证 | Autopsy、Volatility（呼应应急响应取证） |
| 防御 | Snort/Suricata、OSSEC、fail2ban、Lynis、AIDE |
| 实验室 | 隔离网络 + Kali + 靶机（DVWA/Vulhub）+ 防御机 |
| 心态 | 理解原理、防御视角、合规第一、持续学习 |

---

## 本章练习

1. 列出 5 类安全工具及其代表，说明各自用途。
2. 用 `nmap -sV 127.0.0.1` 扫描本机（授权环境），对比 `ss -tuln` 的结果。
3. 用 tcpdump 抓一次 HTTP 流量，观察明文传输（自己环境）。
4. 用 OpenSSL 计算一个文件的 SHA256 哈希。
5. 用 Docker 搭建一个 DVWA 靶场（在自己的隔离环境）。
6. 安装 Lynis 和 fail2ban，对你的实验机做一次审计。
7. 规划一个隔离的安全实验网络（画出攻击机/靶机/防御机的拓扑）。
8. 思考：为什么说"学攻击是为了更好地防守"？作为安全从业者，合规边界为什么如此重要？

---

**下一章预告**：第六卷结束，进入最后的第七卷——综合实战。我们将做三个完整项目：Linux 安全加固脚本、日志分析入侵检测系统、以及 AI + 安全的 Linux 服务器防护体系，把全套知识串成完整能力。
