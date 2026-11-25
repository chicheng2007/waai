# 第 18 章 防火墙：iptables / nftables / firewalld

## 本章目标

读完这一章，你将能够：

- 理解防火墙与 Netfilter 的工作原理
- 理解链（chain）、规则（rule）、表（table）的概念
- 掌握 iptables 的基本使用（过滤、NAT）
- 了解 nftables（新一代）与 firewalld（易用封装）
- 编写安全的防火墙规则（默认拒绝、最小开放）
- 用防火墙防御常见攻击（暴力破解、扫描）

---

## 18.1 防火墙基础

### 18.1.1 什么是防火墙

防火墙是控制网络进出流量的机制。它根据规则决定：这个数据包是放行（ACCEPT）、丢弃（DROP）、拒绝（REJECT）还是转发。

比喻：防火墙就像小区的门禁，检查每个进出的人，符合规则的放行，可疑的拦下。

### 18.1.2 Netfilter：内核里的防火墙框架

Linux 的防火墙功能由内核的 **Netfilter** 框架提供。我们用的 iptables/nftables/firewalld 都是"配置 Netfilter 的工具"。

数据包在内核里经过几个"钩子点（hook）"：

```
数据包 → PREROUTING → [路由判断] → INPUT（发给本机）
                                  → FORWARD（转发）
                                  → OUTPUT（本机发出） → POSTROUTING
```

- **INPUT**：进入本机的数据包（别人访问你的服务）
- **OUTPUT**：本机发出的数据包（你访问别人）
- **FORWARD**：经过本机转发的数据包（本机当路由器）

我们做服务器防护，主要关注 **INPUT 链**——谁能连进来。

### 18.1.3 三种动作

| 动作 | 效果 |
|------|------|
| ACCEPT | 放行 |
| DROP | 丢弃（不发任何回应，对方只能超时） |
| REJECT | 拒绝（发回错误响应，对方立即知道被拒） |

> **安全提示**：对外来扫描，用 DROP 比 REJECT 更好——不给攻击者明确的"端口关闭"反馈，增加其扫描成本。但对内网合法用户，REJECT 更友好。

---

## 18.2 iptables 基础

### 18.2.1 查看规则

```bash
sudo iptables -L              # 列出所有规则
sudo iptables -L -n           # 数字形式显示 IP/端口（不解析域名，更快）
sudo iptables -L -n -v        # 详细（显示包计数）
sudo iptables -L --line-numbers  # 显示规则编号（删除时用）
sudo iptables -S              # 以命令形式列出
```

### 18.2.2 规则语法

```bash
iptables -A 链 -p 协议 --dport 端口 -j 动作
```

| 参数 | 含义 |
|------|------|
| `-A` | 追加规则（append）；`-I` 插入；`-D` 删除 |
| `链` | INPUT / OUTPUT / FORWARD |
| `-p` | 协议：tcp / udp / icmp / all |
| `--dport` | 目标端口 |
| `-s` | 源地址 |
| `-d` | 目标地址 |
| `-j` | 动作：ACCEPT / DROP / REJECT |

### 18.2.3 常用规则示例

```bash
# 允许本地回环（很重要，否则本机服务互访可能出问题）
sudo iptables -A INPUT -i lo -j ACCEPT

# 允许已建立的相关连接（关键！让响应的包能回来）
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 开放 SSH（22 端口）——远程管理必须，否则把自己锁在外面
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 开放 HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许 ping
sudo iptables -A INPUT -p icmp -j ACCEPT

# 默认拒绝所有进入（最后一条，兜底）
sudo iptables -A INPUT -j DROP
```

> ⚠️ **最重要的警告**：**顺序决定一切**。iptables 从上到下匹配，一旦匹配就停止。所以"默认拒绝"必须放最后。如果先加了 DROP，后面的 ACCEPT 全都没用。
>
> 更要命的是：**如果你通过 SSH 连接服务器，一定要先允许 22 端口（或你的管理 IP），再加默认 DROP**，否则会把自己锁在外面！

### 18.2.4 删除与清空

```bash
sudo iptables -L --line-numbers       # 先看编号
sudo iptables -D INPUT 3             # 删除 INPUT 链第 3 条规则

sudo iptables -F                     # 清空所有规则（Flush）⚠️ 危险
sudo iptables -X                     # 删除自定义链
```

### 18.2.5 保存规则

iptables 规则重启后丢失，需要保存：

```bash
# Debian/Ubuntu
sudo apt install iptables-persistent
sudo netfilter-persistent save

# 或手工
sudo iptables-save > /etc/iptables/rules.v4
```

恢复：

```bash
sudo iptables-restore < /etc/iptables/rules.v4
```

### 18.2.6 NAT（网络地址转换）

```bash
# 开启 IP 转发
sudo sysctl -w net.ipv4.ip_forward=1

# SNAT/MASQUERADE：让内网机器通过本机上网
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
```

> **小白问**：`-t nat` 是什么？
>
> iptables 有多个表：filter（默认，过滤）、nat（地址转换）、mangle（修改包）等。`-t nat` 指定操作 nat 表。日常防火墙用默认的 filter 表即可。

---

## 18.3 用 iptables 防御攻击

### 18.3.1 限制 SSH 暴力破解

```bash
# 限制：同一 IP 一分钟内最多 3 个新 SSH 连接，超过则丢弃
sudo iptables -A INPUT -p tcp --dport 22 -m state --state NEW \
  -m recent --set --name SSH
sudo iptables -A INPUT -p tcp --dport 22 -m state --state NEW \
  -m recent --update --seconds 60 --hitcount 4 --name SSH -j DROP
```

`recent` 模块记录连接来源，`--hitcount 4` 表示第 4 次起丢弃。这能有效减缓暴力破解。

### 18.3.2 只允许特定 IP 访问敏感端口

```bash
# 只允许 192.168.1.100 访问 MySQL（3306）
sudo iptables -A INPUT -p tcp --dport 3306 -s 192.168.1.100 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 3306 -j DROP
```

### 18.3.3 防御 SYN Flood

```bash
# 限制 SYN 请求速率
sudo iptables -A INPUT -p tcp --syn -m limit --limit 10/second -j ACCEPT
sudo iptables -A INPUT -p tcp --syn -j DROP
```

### 18.3.4 阻止 ping（防探测）

```bash
sudo iptables -A INPUT -p icmp --icmp-type echo-request -j DROP
```

---

## 18.4 nftables：新一代防火墙

nftables 是 iptables 的继任者，语法更统一、性能更好，Ubuntu 22.04 已默认使用 nftables 后端（iptables 命令实际是兼容层）。

基本操作：

```bash
sudo nft list ruleset              # 查看所有规则
sudo nft add table inet filter     # 创建表
sudo nft add chain inet filter input '{ type filter hook input priority 0; }'
sudo nft add rule inet filter input iif lo accept
sudo nft add rule inet filter input ct state established,related accept
sudo nft add rule inet filter input tcp dport 22 accept
sudo nft add rule inet filter input drop
```

语法差异：

| 概念 | iptables | nftables |
|------|---------|---------|
| 表 | 内置固定 | 自定义 |
| 链 | 内置固定 | 自定义，指定 hook |
| 规则 | `-p tcp --dport 22 -j ACCEPT` | `tcp dport 22 accept` |

> **学哪个？** 如果只需配置常规防火墙，firewalld/ufw 最简单；如果要精细控制，iptables 资料最多；面向未来，nftables 是趋势。本教程以 iptables 为主讲原理，实操推荐用 ufw/firewalld 降低出错风险。

---

## 18.5 ufw：Ubuntu 的简易防火墙

Ubuntu 提供 `ufw`（Uncomplicated Firewall），对 iptables 做了傻瓜化封装，适合快速上手：

```bash
sudo ufw status                # 查看状态
sudo ufw enable                # 启用（⚠️ 先确保 SSH 已允许）
sudo ufw disable               # 关闭

sudo ufw allow 22/tcp          # 允许 SSH
sudo ufw allow 80/tcp          # 允许 HTTP
sudo ufw allow from 192.168.1.100 to any port 3306   # 只允许特定 IP 访问 MySQL

sudo ufw default deny incoming # 默认拒绝进入
sudo ufw default allow outgoing # 默认允许外出

sudo ufw delete allow 80/tcp   # 删除规则
sudo ufw status numbered       # 带编号查看
```

> **记住**：`sudo ufw enable` 前，一定先 `sudo ufw allow 22/tcp`（或你的 SSH 端口），否则会把自己锁在外面。这是新手最常犯的错误。

---

## 18.6 firewalld：RHEL 系的防火墙

CentOS/RHEL/Fedora 使用 firewalld，基于"区域（zone）"和"服务（service）"的概念：

```bash
sudo systemctl status firewalld
sudo firewall-cmd --state                    # 查看状态
sudo firewall-cmd --get-active-zones         # 查看活动区域
sudo firewall-cmd --list-all                 # 列出当前区域所有配置

# 永久开放服务/端口
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload                   # 重新加载生效

# 富规则（更精细）
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.100" port port="3306" protocol="tcp" accept'
```

---

## 18.7 防火墙最佳实践

### 18.7.1 默认拒绝原则

> 默认拒绝所有，只开放必需的端口和服务。这叫"默认拒绝（default deny）"，是最安全的基线。

### 18.7.2 防火墙检查清单

```bash
# 1. 看当前开放了哪些端口
sudo ss -tuln

# 2. 看防火墙规则
sudo iptables -L -n
# 或
sudo ufw status

# 3. 从外部扫描自己（在授权环境）
nmap -sT 你的服务器IP

# 4. 确认只开放了必要端口
```

### 18.7.3 常见错误

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 没先允许 SSH 就启用默认拒绝 | 把自己锁在外面 | 先允许 22，再拒绝 |
| 规则顺序错（DROP 在 ACCEPT 前） | 后面的允许规则失效 | 允许规则在前，拒绝兜底 |
| 规则没保存 | 重启后失效 | `netfilter-persistent save` |
| 开放了数据库端口到公网 | 数据库暴露被攻击 | 只允许特定 IP 或内网 |

---

## 18.8 本章总结

| 知识点 | 内容 |
|--------|------|
| Netfilter | 内核防火墙框架；hook 点：INPUT/OUTPUT/FORWARD |
| 动作 | ACCEPT 放行、DROP 丢弃（无回应）、REJECT 拒绝（有回应） |
| iptables | `-A` 追加、`-p` 协议、`--dport` 端口、`-s` 源、`-j` 动作 |
| 顺序 | 从上到下匹配，允许在前、拒绝兜底；先开 SSH 再启用 |
| 保存 | `netfilter-persistent save` / `iptables-save` |
| nftables | 新一代，语法统一，是趋势 |
| ufw | Ubuntu 简易封装，`ufw allow 22/tcp` |
| firewalld | RHEL 系，zone + service，`firewall-cmd` |
| 原则 | 默认拒绝、最小开放、防暴力破解、定期检查 |

---

## 本章练习

1. 用 `sudo iptables -L -n` 查看你系统的规则（如果是新系统可能为空）。
2. 用 `sudo ss -tuln` 查看当前监听端口。
3. （在虚拟机里）用 ufw 设置：允许 SSH、HTTP，默认拒绝进入，然后查看状态。
4. 写一条 iptables 规则：只允许 127.0.0.1 访问 3306 端口。
5. 理解 iptables 规则顺序的重要性：如果把 DROP 放第一条会怎样？
6. 用 `nmap -sT 127.0.0.1` 扫描本机（授权环境），对比防火墙规则。
7. 思考：为什么远程服务器配置防火墙时，第一步总是"允许 SSH"？
8. 思考：DROP 和 REJECT 对攻击者反馈的信息有何不同？哪种更适合对外防御？

---

**下一章预告**：我们将学习 SSH 安全与远程访问——SSH 是远程管理服务器的生命线，也是攻击者的重点目标。如何加固 SSH、防止暴力破解、密钥登录，是服务器安全的核心课题。
