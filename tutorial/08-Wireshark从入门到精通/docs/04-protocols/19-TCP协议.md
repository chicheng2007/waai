# 第十九章 TCP 协议深度解析

TCP（Transmission Control Protocol，传输控制协议）是互联网最重要的传输层协议。它为应用提供**面向连接、可靠、有序、字节流**的传输服务。绝大多数关键应用（Web、邮件、文件传输、远程登录）都基于 TCP。本章是全书最重要的一章，我们将深入剖析 TCP 的报文结构、连接管理、可靠性机制，以及在 Wireshark 中如何分析 TCP 流量。

## 19.1 TCP 的特点

- **面向连接**：通信前必须建立连接（三次握手），结束后释放连接（四次挥手）。
- **可靠传输**：通过序列号、确认应答、重传机制保证数据不丢失、不重复、按序到达。
- **流量控制**：通过滑动窗口机制，接收方告知发送方自己能处理多少数据。
- **拥塞控制**：根据网络状况动态调整发送速率，避免加剧网络拥塞。
- **全双工**：连接双方可以同时收发数据。
- **面向字节流**：不保留消息边界，数据被视为连续的字节流。

## 19.2 TCP 报文段结构

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Acknowledgment Number                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Data |           |U|A|P|R|S|F|                               |
| Offset| Reserved  |R|C|S|S|Y|I|            Window             |
|       |           |G|K|H|T|N|N|                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Checksum            |         Urgent Pointer          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options (if any)                             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             Data                                |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 19.2.1 关键字段

| 字段 | 长度 | 含义 |
| --- | --- | --- |
| Source Port | 16 位 | 源端口 |
| Destination Port | 16 位 | 目的端口 |
| Sequence Number | 32 位 | 序列号，标识本报文段第一个数据字节的序号 |
| Acknowledgment Number | 32 位 | 确认号，期望收到的下一个字节序号 |
| Data Offset | 4 位 | TCP 首部长度，单位 4 字节 |
| Flags | 8 位（6 个有效位） | URG、ACK、PSH、RST、SYN、FIN |
| Window | 16 位 | 接收窗口大小，用于流量控制 |
| Checksum | 16 位 | 校验和（伪首部 + TCP 首部 + 数据） |
| Urgent Pointer | 16 位 | 紧急指针（配合 URG） |
| Options | 可变 | MSS、窗口扩大因子、SACK、时间戳等 |

### 19.2.2 六个标志位

| 标志 | 全称 | 含义 |
| --- | --- | --- |
| SYN | Synchronize | 发起连接，同步序列号 |
| ACK | Acknowledgment | 确认号有效 |
| FIN | Finish | 请求关闭连接 |
| RST | Reset | 重置连接（异常终止） |
| PSH | Push | 尽快交付给应用（不缓存） |
| URG | Urgent | 紧急数据 |

Wireshark 的 Info 列会用方括号显示标志组合，如 `[SYN]`、`[SYN, ACK]`、`[PSH, ACK]`、`[RST, ACK]`、`[FIN, ACK]`。

### 19.2.3 重要选项

- **MSS（Maximum Segment Size）**：最大报文段长度，通常在 SYN 包中通告，一般是 MTU - IP 首部 - TCP 首部 = 1500 - 20 - 20 = 1460 字节。
- **Window Scale（窗口扩大因子）**：把 16 位窗口左移若干位，支持更大窗口（高速网络必需）。
- **SACK（Selective Acknowledgment）**：选择性确认，只确认收到的片段，提高重传效率。
- **Timestamps（时间戳）**：用于精确计算 RTT 和检测乱序。
- **NOP**：填充选项，1 字节。

在 Wireshark 中展开 `[TCP Options]` 可以看到这些选项的值。

## 19.3 三次握手（连接建立）

TCP 建立连接需要三次报文交换：

```
客户端                                      服务器
   |                                           |
   |---------- SYN (Seq=x) ------------------->|   1. 客户端发送 SYN
   |                                           |
   |<--------- SYN+ACK (Seq=y, Ack=x+1) -------|   2. 服务器回复 SYN+ACK
   |                                           |
   |---------- ACK (Ack=y+1) ----------------->|   3. 客户端发送 ACK
   |                                           |
   |<======== 连接建立，开始数据传输 ==========>|
```

### 19.3.1 逐步解析

**第一次握手**：客户端发送 SYN 包。

```
Flags: 0x002 (SYN)
Sequence Number: 0 (relative sequence number)
[Next Sequence Number: 1]
Acknowledgment Number: 0
Options: MSS=1460, SACK Permitted, Window Scale=7, Timestamps, NOP
Window: 64240
```

客户端进入 SYN-SENT 状态。序列号 x 是随机初始值（ISN，Initial Sequence Number）。Wireshark 默认显示**相对序列号**（relative sequence number），把 ISN 归零，便于阅读。

**第二次握手**：服务器回复 SYN+ACK。

```
Flags: 0x012 (SYN, ACK)
Sequence Number: 0 (relative sequence number)
Acknowledgment Number: 1 (relative ack number)
Options: MSS=1460, SACK Permitted, Window Scale=7, Timestamps, NOP
Window: 65535
```

服务器进入 SYN-RECEIVED 状态。确认号 x+1 表示「已收到客户端的 SYN，下一个期望字节是 x+1」。

**第三次握手**：客户端发送 ACK。

```
Flags: 0x010 (ACK)
Sequence Number: 1 (relative sequence number)
Acknowledgment Number: 1 (relative ack number)
Window: 64240
```

客户端和服务器都进入 ESTABLISHED 状态，连接建立完成。第三次握手可以携带数据（如 HTTP 请求有时就跟在这一步）。

### 19.3.2 为什么要三次握手

核心目的是**双方都确认对方的发送和接收能力正常**：

- 第一次：服务器知道客户端能发。
- 第二次：客户端知道服务器能收、能发。
- 第三次：服务器知道客户端能收。

同时，三次握手交换初始序列号（ISN），为可靠传输奠定基础，并防止旧的重复连接请求造成混乱。

### 19.3.3 在 Wireshark 中查看握手

过滤某一 TCP 流：

```
tcp.stream eq 0
```

或者右键任意 TCP 包 → `Follow → TCP Stream`，然后关闭流内容窗口，列表就只剩下该流的包。

列表中的前三个包就是三次握手。Info 列显示 `[SYN]`、`[SYN, ACK]`、`[ACK]`。

**握手异常分析**：

| 现象 | 可能原因 |
| --- | --- |
| 只有 SYN，没有 SYN+ACK | 服务器不在线、防火墙丢弃、端口未监听 |
| SYN 后收到 RST | 端口关闭或服务拒绝 |
| SYN 重传多次 | 服务器无响应、网络丢包、SYN Flood |
| SYN+ACK 后没有 ACK | 客户端问题（如被防火墙拦截 ACK） |

## 19.4 四次挥手（连接释放）

TCP 连接是全双工的，关闭时每个方向都要单独关闭，因此需要四次报文：

```
客户端                                      服务器
   |                                           |
   |---------- FIN+ACK ----------------------->|   1. 客户端请求关闭
   |                                           |
   |<--------- ACK ----------------------------|   2. 服务器确认
   |                                           |
   |<--------- FIN+ACK ------------------------|   3. 服务器请求关闭
   |                                           |
   |---------- ACK --------------------------->|   4. 客户端确认
   |                                           |
   |<======== 连接完全关闭 =====================>|
```

### 19.4.1 状态变化

1. 客户端发送 FIN，进入 FIN-WAIT-1。
2. 服务器收到 FIN，发送 ACK，进入 CLOSE-WAIT；客户端收到 ACK 进入 FIN-WAIT-2。
3. 服务器发送自己的 FIN，进入 LAST-ACK；客户端收到后进入 TIME-WAIT。
4. 客户端发送 ACK，服务器进入 CLOSED；客户端等待 2MSL 后进入 CLOSED。

### 19.4.2 TIME-WAIT 的作用

客户端在发送最后一个 ACK 后要等待 2MSL（Maximum Segment Lifetime，通常 60 秒~2 分钟），原因：

- 确保最后一个 ACK 能到达服务器（如果丢失，服务器会重发 FIN，客户端还有机会回应）。
- 让本次连接的残余报文在网络中消散，避免影响新连接。

### 19.4.3 挥手异常

| 现象 | 可能原因 |
| --- | --- |
| 只有 FIN 没有响应 | 对端不响应、网络中断 |
| 收到 RST 而非 FIN | 异常终止（如进程崩溃、超时） |
| 大量 TIME-WAIT | 短连接过多（常见于高并发服务器） |
| FIN 反复重传 | 对端 ACK 丢失 |

## 19.5 可靠性机制

### 19.5.1 序列号与确认号

TCP 把数据视为字节流，每个字节都有序号。确认号表示「期望收到的下一个字节序号」，即「此前所有字节都已收到」。

例如：发送方发送 Seq=1001、长度 100 字节的数据，接收方收到后回复 Ack=1101。

Wireshark 默认显示**相对序号**（从 0 开始），便于观察。如需看绝对序号，可在 `Edit → Preferences → Protocols → TCP` 中取消勾选「Relative sequence numbers」。

### 19.5.2 重传机制

TCP 在以下情况触发重传：

1. **超时重传（Retransmission）**：发送后未在 RTO（重传超时）内收到 ACK。
2. **快速重传（Fast Retransmission）**：收到 3 个重复 ACK，说明中间有包丢失。
3. **SACK 重传**：根据 SACK 信息只重传真正丢失的片段。

Wireshark 会明确标注：

```
[TCP Retransmission] 54321 → 80 [PSH, ACK] Seq=1 Ack=1 Win=64240 Len=458
[TCP Fast Retransmission] ...
[TCP Dup ACK 3#1] ...      # 重复 ACK
[TCP Spurious Retransmission] ...  # 虚假重传（数据其实已收到）
```

**重传分析是网络排障的重点**：

```
tcp.analysis.retransmission           # 所有重传
tcp.analysis.fast_retransmission      # 快速重传
tcp.analysis.duplicate_ack            # 重复 ACK
tcp.analysis.spurious_retransmission  # 虚假重传
tcp.analysis.out_of_order             # 乱序
```

大量重传通常意味着链路丢包、拥塞、设备故障或无线信号差。

### 19.5.3 RTT 与 RTO

- **RTT（Round-Trip Time）**：包发出到收到 ACK 的时间。
- **RTO（Retransmission Timeout）**：基于 RTT 动态计算的超时时间。

Wireshark 可以显示 TCP RTT：

```
tcp.analysis.ack_rtt                  # ACK 对应的 RTT
```

在 `Statistics → TCP Stream Graphs → Round Trip Time` 可以看到 RTT 随时间变化的图表。

## 19.6 流量控制与滑动窗口

TCP 使用滑动窗口实现流量控制：接收方在 ACK 中通告自己的接收窗口（Window 字段），发送方发送的数据量不能超过该窗口。

- 窗口大：接收方处理能力强，发送方可多发。
- 窗口小：接收方处理慢，发送方需减速。
- 窗口为 0（Zero Window）：接收方缓冲区满，发送方必须停止发送。

Wireshark 中检测零窗口：

```
tcp.window_size == 0
tcp.analysis.zero_window               # 零窗口事件
tcp.analysis.window_update             # 窗口更新
```

**零窗口是性能问题的强烈信号**：说明接收方应用处理不过来，可能导致发送方长时间等待，吞吐量骤降。

## 19.7 拥塞控制

拥塞控制防止发送方过度注入数据导致网络拥塞，主要机制：

- **慢启动（Slow Start）**：连接开始时拥塞窗口（cwnd）从小值开始指数增长。
- **拥塞避免（Congestion Avoidance）**：达到阈值后线性增长。
- **快重传与快恢复**：收到 3 个重复 ACK 时快速重传并降低 cwnd。

Wireshark 无法直接看到 cwnd（它是发送方的内部状态），但可以通过发送速率、重传模式间接推断。

## 19.8 TCP 分析实战流程

分析一个 TCP 连接问题的标准流程：

1. **过滤出目标流**：`tcp.stream eq N` 或 Follow TCP Stream。
2. **看三次握手**：确认连接建立成功，记录 MSS、窗口扩大因子等参数。
3. **看数据传输**：观察 Seq/Ack 是否连续，有无重传、乱序。
4. **看专家信息**：`Analyze → Expert Information` 汇总了所有错误/警告。
5. **看统计图表**：`Statistics → TCP Stream Graphs` 提供时序图、吞吐量、RTT、窗口大小等视图。
6. **看四次挥手**：确认连接正常关闭，还是被 RST 中断。

## 19.9 小结

- TCP 提供面向连接、可靠、有序的字节流传输。
- 关键字段：序列号、确认号、标志位（SYN/ACK/FIN/RST/PSH/URG）、窗口、选项（MSS/SACK/时间戳）。
- 三次握手建立连接，交换 ISN；四次挥手关闭全双工连接，客户端需等待 2MSL。
- 可靠性靠序列号、确认、重传（超时/快速/SACK）实现。
- 流量控制靠滑动窗口，零窗口是性能瓶颈信号。
- Wireshark 用 `tcp.analysis.*` 系列字段标注重传、重复 ACK、乱序、零窗口等异常。

下一章，我们看 UDP——TCP 的「简约兄弟」。
