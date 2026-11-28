# 第十八章 IPv6 与 ICMP

本章介绍 IPv6 协议的基础与 ICMP 协议族。IPv6 是下一代互联网协议，ICMP 则是网络诊断与错误报告的核心工具。理解它们，你就能看懂 ping、traceroute 以及各种网络错误背后的包。

## 18.1 IPv6 基础

### 18.1.1 为什么需要 IPv6

IPv4 地址只有 32 位（约 43 亿个），早已耗尽。IPv6 使用 128 位地址，数量达到 2^128 个，号称「可以为地球上每一粒沙子分配一个地址」。此外 IPv6 还改进了首部格式、支持自动配置、内置安全性（IPsec）等。

### 18.1.2 IPv6 地址表示

IPv6 地址写成 8 组 4 位十六进制数，用冒号分隔：

```
2001:0db8:85a3:0000:0000:8a2e:0370:7334
```

简化规则：

- 前导零可省略：`2001:db8:85a3:0:0:8a2e:370:7334`
- 连续的全零组可用 `::` 代替（只能用一次）：`2001:db8:85a3::8a2e:370:7334`

特殊地址：

- `::1`：回环地址（等价 IPv4 的 127.0.0.1）
- `fe80::/10`：链路本地地址
- `2001:db8::/32`：文档示例地址
- `ff00::/8`：组播地址

### 18.1.3 IPv6 首部结构

IPv6 首部固定 40 字节：

```
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Version| Traffic Class |           Flow Label                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Payload Length        |  Next Header  |  Hop Limit    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                       Source Address (16 字节)                |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
|                    Destination Address (16 字节)              |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

相比 IPv4，IPv6 做了简化：

- 去掉了 IHL（首部长度固定 40 字节）。
- 去掉了首部校验和（由链路层和传输层负责）。
- 去掉了分片相关字段（分片改为扩展首部处理）。
- TTL 改名为 Hop Limit（跳数限制）。
- Protocol 改名为 Next Header（下一个首部类型）。

### 18.1.4 扩展首部

IPv6 把可选功能放到**扩展首部**中，通过 Next Header 链式连接：

- Hop-by-Hop Options（逐跳选项）
- Routing（路由）
- Fragment（分片）
- Destination Options（目的选项）
- Authentication Header / ESP（IPsec）

Wireshark 会逐层展开这些扩展首部。

### 18.1.5 Wireshark 中的 IPv6 包

过滤器：

```
ipv6                                 # 所有 IPv6 包
ipv6.addr == 2001:db8::1             # 特定 IPv6 地址
ipv6.src == fe80::1                  # 源地址
ipv6.hop_limit == 64                 # 跳数限制
icmpv6                               # ICMPv6
```

协议详情窗格示例：

```
Internet Protocol Version 6, Src: 2001:db8::1, Dst: 2001:db8::2
    0110 .... = Version: 6
    .... 0000 0000 ................ = Traffic Class: 0x00
    .... .... .... 0000 0000 0000 0000 0000 = Flow Label: 0x00000
    Payload Length: 20
    Next Header: ICMPv6 (58)
    Hop Limit: 64
    Source Address: 2001:db8::1
    Destination Address: 2001:db8::2
```

## 18.2 ICMP 协议

### 18.2.1 ICMP 的作用

ICMP（Internet Control Message Protocol，互联网控制报文协议）用于在 IP 网络中传递**控制消息和错误报告**。它不传输用户数据，而是报告网络层的问题，如目的不可达、超时、重定向等。ping 和 traceroute 都依赖 ICMP。

### 18.2.2 ICMP 报文格式

```
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Type      |     Code      |           Checksum             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      消息内容（可变）                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **Type（类型）**：报文大类。
- **Code（代码）**：对 Type 的进一步细化。
- **Checksum**：校验和。

### 18.2.3 常见 ICMP 类型

| Type | Code | 含义 | 典型场景 |
| --- | --- | --- | --- |
| 0 | 0 | Echo Reply | ping 响应 |
| 3 | 0 | 目的网络不可达 | 路由错误 |
| 3 | 1 | 目的主机不可达 | ARP 失败/主机离线 |
| 3 | 3 | 目的端口不可达 | UDP 端口关闭 |
| 3 | 4 | 需要分片但 DF 置位 | PMTUD（见第十七章） |
| 5 | 0/1 | 重定向 | 路由优化 |
| 8 | 0 | Echo Request | ping 请求 |
| 11 | 0 | TTL 超时（传输中） | traceroute |
| 11 | 1 | TTL 超时（重组时） | 分片重组超时 |
| 12 | — | 参数错误 | 首部字段非法 |

### 18.2.4 ping 的抓包分析

执行 `ping 8.8.8.8`，在 Wireshark 中过滤 `icmp`：

```
Internet Control Message Protocol
    Type: 8 (Echo (ping) request)
    Code: 0
    Checksum: 0x1234 [correct]
    [Checksum Status: Good]
    Identifier (BE): 1 (0x0001)
    Identifier (LE): 256 (0x0100)
    Sequence Number (BE): 1 (0x0001)
    Sequence Number (LE): 256 (0x0100)
    [Response frame: 5]
    Data (32 bytes)
```

每个 ping 包含：

- **Identifier**：区分不同的 ping 进程。
- **Sequence Number**：序号，匹配请求与响应。
- **Data**：填充数据（通常是字母序列或时间戳）。

Wireshark 会用 `[Response frame: N]` 或 `[Request frame: N]` 标注对应的请求/响应包，非常方便。

**ping 分析要点**：

- 是否有 Echo Request 但没有 Reply（网络不通/防火墙拦截）。
- 请求与响应的时间间隔（RTT）。
- 是否有丢包（序号跳跃）。
- TTL 值（推算跳数、识别系统）。

### 18.2.5 traceroute 原理

traceroute 巧妙利用 ICMP TTL 超时消息：

1. 发送 TTL=1 的包（UDP 高端口或 ICMP Echo）到目的地址。
2. 第一跳路由器把 TTL 减到 0，丢弃包，返回 ICMP Type 11 Code 0（超时）。
3. 发送 TTL=2 的包，第二跳路由器返回超时。
4. 依次递增，直到到达目的主机（返回 ICMP 端口不可达或 Echo Reply）。

Wireshark 中过滤 `icmp.type == 11` 可以看到路由器返回的超时消息，其中 `Source Address` 就是每一跳路由器的 IP。

## 18.3 ICMPv6

ICMPv6（协议号 58）在 IPv6 中不仅承担 ICMP 的功能，还整合了 ARP 的功能（通过邻居发现协议 NDP）：

| ICMPv6 Type | 含义 |
| --- | --- |
| 1 | 目的不可达 |
| 2 | 包太大（Packet Too Big，用于 PMTUD） |
| 3 | 超时 |
| 128 | Echo Request |
| 129 | Echo Reply |
| 133 | 路由器请求（RS） |
| 134 | 路由器通告（RA） |
| 135 | 邻居请求（NS，类似 ARP 请求） |
| 136 | 邻居通告（NA，类似 ARP 响应） |

**NDP（邻居发现协议）** 用 ICMPv6 的 NS/NA 消息替代了 IPv4 的 ARP。在 Wireshark 中过滤 `icmpv6.type == 135 || icmpv6.type == 136` 可以看到邻居发现过程。

**路由器通告（RA）** 是 IPv6 自动配置（SLAAC）的基础。恶意 RA 攻击（伪造路由器通告）是 IPv6 网络安全的一个常见问题。

## 18.4 小结

- IPv6 使用 128 位地址，首部固定 40 字节，去掉了校验和和分片字段，用扩展首部实现可选功能。
- ICMP 用于传递控制消息和错误报告，ping 和 traceroute 依赖它。
- 常见 ICMP 类型：8/0（ping 请求/响应）、3（目的不可达）、11（超时）、5（重定向）。
- ping 分析关注请求/响应配对、RTT、丢包、TTL。
- traceroute 利用 TTL 超时逐跳发现路径。
- ICMPv6 整合了 NDP（替代 ARP），Type 135/136 对应邻居请求/通告。

下一章是全书最重要的一章——TCP 协议深度解析。
