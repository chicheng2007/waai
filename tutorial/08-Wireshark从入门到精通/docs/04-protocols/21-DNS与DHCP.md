# 第二十一章 DNS 与 DHCP

DNS（域名系统）和 DHCP（动态主机配置协议）是网络中最基础的两个服务。DNS 把域名解析为 IP，DHCP 为主机自动分配网络配置。本章详细解析它们的报文结构、交互流程，以及在 Wireshark 中的分析方法。

## 21.1 DNS 协议

### 21.1.1 DNS 的作用与结构

DNS（Domain Name System）是互联网的「电话簿」，把人类可读的域名（如 `www.example.com`）解析为机器可用的 IP 地址。DNS 采用分布式、层次化架构：

- **根域名服务器**（.）：顶层。
- **顶级域服务器**（.com、.cn、.org 等）。
- **权威域名服务器**：管理具体域名的记录。
- **本地 DNS 解析器**（递归解析器）：运营商或公共 DNS（如 8.8.8.8、114.114.114.114）。

### 21.1.2 DNS 报文格式

```
┌─────────────────────────────────────────────┐
│              Header（12 字节）               │
├─────────────────────────────────────────────┤
│           Question（查询问题）               │
├─────────────────────────────────────────────┤
│           Answer（回答记录）                 │
├─────────────────────────────────────────────┤
│           Authority（权威记录）              │
├─────────────────────────────────────────────┤
│           Additional（附加记录）             │
└─────────────────────────────────────────────┘
```

Header 包含：

- **Transaction ID**：事务 ID，匹配查询与响应。
- **Flags**：标志位，包含 QR（查询/响应）、Opcode、AA（权威回答）、TC（截断）、RD（期望递归）、RA（支持递归）、RCODE（响应码）。
- **计数**：Questions、Answer RRs、Authority RRs、Additional RRs 的数量。

### 21.1.3 Wireshark 中的 DNS 查询

执行 `nslookup www.example.com`，过滤 `dns`：

**查询包**：

```
Domain Name System (query)
    Transaction ID: 0x1234
    Flags: 0x0100 Standard query
        0... .... ... .... = Response: Message is a query
        .000 0... ... .... = Opcode: Standard query (0)
        .... ..1. ... .... = Recursion desired: Do query recursively
    Questions: 1
    Queries
        www.example.com: type A, class IN
            Name: www.example.com
            [Name Length: 15]
            Type: A (1)      # 请求 IPv4 地址
            Class: IN (0x0001)
```

**响应包**：

```
Domain Name System (response)
    Transaction ID: 0x1234
    Flags: 0x8180 Standard query response, No error
        1... .... ... .... = Response: Message is a response
        .... .... .... 0000 = Reply code: No error (0)
    Questions: 1
    Answer RRs: 2
    Answers
        www.example.com: type A, class IN, addr 93.184.216.34
            Name: www.example.com
            Type: A (1)
            Class: IN (0x0001)
            Time to live: 3600 (1 hour)
            Data length: 4
            Address: 93.184.216.34
```

**关键点**：

- Transaction ID 匹配查询与响应。
- Type A = IPv4 地址，AAAA = IPv6，CNAME = 别名，MX = 邮件服务器，NS = 域名服务器，PTR = 反向解析，TXT = 文本记录。
- TTL 指示缓存时间。

### 21.1.4 DNS 查询过程

以访问 `www.example.com` 为例：

1. 浏览器查本地缓存、hosts 文件。
2. 向本地 DNS 服务器发送递归查询。
3. 本地 DNS 如果不知道，依次查询根、顶级域、权威服务器（迭代查询）。
4. 权威服务器返回 IP，本地 DNS 缓存并回复客户端。
5. 客户端缓存结果，开始 TCP 连接。

在 Wireshark 中，如果客户端直接向公共 DNS 查询，通常只看到一问一答；如果本地 DNS 做迭代查询，会看到多组查询/响应。

### 21.1.5 DNS 常用过滤器

```
dns                                      # 所有 DNS 流量
dns.flags.response == 0                  # DNS 查询
dns.flags.response == 1                  # DNS 响应
dns.qry.name == "www.example.com"        # 查询特定域名
dns.qry.name contains "example"          # 域名包含 example
dns.qry.type == 1                        # A 记录查询
dns.qry.type == 28                       # AAAA 查询
dns.a                                    # 含 A 记录响应的包
dns.resp.code != 0                       # 错误响应（NXDOMAIN 等）
dns.time > 0.5                           # 响应超过 0.5 秒（需启用）
```

### 21.1.6 DNS 故障分析

| 现象 | 可能原因 |
| --- | --- |
| 有查询无响应 | DNS 服务器不可达、防火墙拦截 UDP 53 |
| 响应码 3（NXDOMAIN） | 域名不存在 |
| 响应码 2（SERVFAIL） | 服务器内部错误 |
| 响应很慢 | DNS 服务器负载高、递归查询链路长 |
| 返回 IP 不正确 | DNS 劫持、遭污染 |

### 21.1.7 DNS 隧道与安全

DNS 隧道利用 DNS 查询/响应承载其他数据（如把敏感数据编码到子域名中），绕过防火墙。检测思路：

```
len(dns.qry.name) > 50                   # 超长域名
dns.qry.name matches "[a-f0-9]{20,}"     # 疑似编码的子域名
dns.qry.type == 16                       # TXT 记录查询（常用于隧道）
```

DNS 隧道工具（如 iodine、dnscat2）会产生大量异常 DNS 流量，是安全分析的重点。

## 21.2 DHCP 协议

### 21.2.1 DHCP 的作用

DHCP（Dynamic Host Configuration Protocol）为主机自动分配 IP 地址、子网掩码、默认网关、DNS 服务器等网络配置。它基于 UDP，客户端端口 68，服务器端口 67。

### 21.2.2 DHCP 四步交互（DORA）

新主机加入网络时，通过四步获取配置：

```
客户端                                   DHCP 服务器
   |                                         |
   |---- DHCP Discover (广播) -------------->|  1. 发现服务器
   |                                         |
   |<--- DHCP Offer (广播/单播) -------------|  2. 提供配置
   |                                         |
   |---- DHCP Request (广播) --------------->|  3. 请求使用
   |                                         |
   |<--- DHCP ACK (广播/单播) ---------------|  4. 确认分配
   |                                         |
```

**1. DHCP Discover**：客户端广播，寻找可用 DHCP 服务器。源 IP 0.0.0.0，目的 255.255.255.255。

**2. DHCP Offer**：服务器响应，提供一个可用的 IP 地址及配置。

**3. DHCP Request**：客户端广播请求使用某个 Offer（可能有多个服务器响应，客户端选择一个）。

**4. DHCP ACK**：服务器确认，客户端正式使用配置。

### 21.2.3 DHCP 报文结构

DHCP 报文基于 BOOTP 格式：

```
┌──────────┬──────────┬──────┬──────┬─────────────────┐
│ Op       │ Htype    │ Hlen │ Hops │ Transaction ID  │
├──────────┼──────────┼──────┼──────┼─────────────────┤
│ Secs     │ Flags    │ CIaddr(客户端 IP)            │
├──────────────────────┼─────────────────────────────┤
│ Your (yiaddr)        │ Server (siaddr)             │
├──────────────────────┼─────────────────────────────┤
│ Gateway (giaddr)     │ Chaddr(客户端 MAC)          │
├──────────────────────┴─────────────────────────────┤
│ Options（含 DHCP Message Type、子网掩码、网关、DNS、租约时间等）│
└─────────────────────────────────────────────────────┘
```

关键 Options：

- **DHCP Message Type**：1=Discover，2=Offer，3=Request，4=Decline，5=ACK，6=NAK，7=Release，8=Inform。
- **Subnet Mask**：子网掩码。
- **Router**：默认网关。
- **Domain Name Server**：DNS 服务器。
- **IP Address Lease Time**：租约时间。

### 21.2.4 Wireshark 中的 DHCP

过滤 `dhcp` 或 `bootp`。展开协议树：

```
Dynamic Host Configuration Protocol (Discover)
    Message type: Boot Request (1)
    Hardware type: Ethernet (0x01)
    Hardware address length: 6
    Hops: 0
    Transaction ID: 0x12345678
    Seconds elapsed: 0
    Client IP address: 0.0.0.0
    Your (client) IP address: 0.0.0.0
    ...
    Option 53: DHCP Message Type = DHCP Discover
    Option 61: Client identifier
    Option 55: Parameter Request List
```

### 21.2.5 租约续租

DHCP 租约到期前，客户端会续租：

- **T1（租约 50%）**：客户端单播 DHCP Request 给服务器，请求续租。
- **T2（租约 87.5%）**：如果 T1 失败，广播 DHCP Request。

如果续租失败，客户端在租约到期后重新开始 DORA 流程。

### 21.2.6 DHCP 故障分析

| 现象 | 可能原因 |
| --- | --- |
| 只有 Discover 无 Offer | DHCP 服务器不可达、地址池耗尽、VLAN 配置错误 |
| Offer 被 Decline | IP 地址冲突 |
| 收到 DHCP NAK | 服务器拒绝请求（租约过期或配置冲突） |
| 反复 DORA | 租约获取失败、网络连接不稳定 |

过滤器：

```
dhcp                                     # 所有 DHCP
dhcp.option.dhcp == 1                    # Discover
dhcp.option.dhcp == 6                    # NAK
bootp.flags                              # BOOTP 标志
```

## 21.3 小结

- DNS 把域名解析为 IP，采用分布式层次架构，报文含 Header、Question、Answer 等部分。
- DNS 查询/响应通过 Transaction ID 匹配；记录类型 A/AAAA/CNAME/MX/PTR/TXT。
- DNS 故障表现为无响应、NXDOMAIN、SERVFAIL、慢响应等；DNS 隧道是安全分析重点。
- DHCP 自动分配网络配置，基于 UDP（67/68），通过 DORA 四步（Discover/Offer/Request/ACK）获取配置。
- DHCP 报文含 Transaction ID、客户端/服务器 IP、MAC、Options（消息类型、掩码、网关、DNS、租约）。
- 租约在 T1/T2 时续租；故障表现为无 Offer、NAK、反复 DORA 等。

下一章，我们解析 Web 世界的基石——HTTP 协议。
