# 第三十章 tshark 命令行

tshark 是 Wireshark 的命令行版本。它拥有与图形界面相同的协议解析和过滤能力，但没有 GUI，因此非常适合脚本化、批量处理和自动化分析。本章介绍 tshark 的基本用法和实战技巧。

## 30.1 基本用法

### 30.1.1 实时抓包

```bash
# 在 eth0 上抓包，显示每个包的摘要
tshark -i eth0

# 抓 100 个包后停止
tshark -i eth0 -c 100

# 抓包并保存到文件
tshark -i eth0 -w capture.pcapng

# 带捕获过滤器
tshark -i eth0 -f "tcp port 80" -w http.pcapng
```

### 30.1.2 读取抓包文件

```bash
# 读取并显示包摘要
tshark -r capture.pcapng

# 应用显示过滤器
tshark -r capture.pcapng -Y "http"

# 限制显示包数
tshark -r capture.pcapng -Y "dns" -c 10
```

## 30.2 常用参数

| 参数 | 含义 |
| --- | --- |
| `-i <接口>` | 指定捕获接口 |
| `-w <文件>` | 保存到文件 |
| `-r <文件>` | 读取文件 |
| `-f <BPF>` | 捕获过滤器 |
| `-Y <过滤器>` | 显示过滤器 |
| `-c <数量>` | 捕获/显示指定数量的包后停止 |
| `-a <条件>` | 自动停止条件（duration:60, filesize:1000000） |
| `-T <格式>` | 输出格式（fields、json、pdml、text） |
| `-e <字段>` | 输出指定字段（配合 -T fields） |
| `-E <参数>` | 输出选项（separator、quote 等） |
| `-q` | 安静模式（配合 -z 统计） |
| `-z <统计>` | 执行统计 |
| `-V` | 显示详细的协议树 |
| `-x` | 显示十六进制转储 |
| `-D` | 列出可用接口 |

## 30.3 字段提取（-T fields）

这是 tshark 最强大的功能之一：提取指定字段，输出为结构化数据。

```bash
# 提取 DNS 查询的域名
tshark -r capture.pcapng -Y "dns.qry.name" -T fields -e frame.number -e dns.qry.name

# 输出示例：
# 5	www.example.com
# 8	api.example.com
```

```bash
# 提取 HTTP 请求的方法和 URI
tshark -r capture.pcapng -Y "http.request" -T fields \
  -e frame.time -e ip.src -e http.request.method -e http.host -e http.request.uri
```

```bash
# 自定义分隔符（默认制表符）
tshark -r capture.pcapng -Y "tcp.flags.syn==1 && tcp.flags.ack==0" \
  -T fields -e ip.src -e ip.dst -E separator=,
```

`-e` 指定的字段名与 Wireshark 显示过滤器中的字段名完全一致。这是连接图形界面和命令行的桥梁。

## 30.4 输出格式

```bash
# JSON 格式（便于程序处理）
tshark -r capture.pcapng -Y "http" -T json > http.json

# 详细协议树
tshark -r capture.pcapng -Y "dns" -V | head -100

# 十六进制转储
tshark -r capture.pcapng -c 1 -x

# PDML（XML 格式，含完整字段结构）
tshark -r capture.pcapng -T pdml > output.pdml
```

## 30.5 统计功能（-z）

tshark 可以在命令行执行统计：

```bash
# 协议分层统计
tshark -r capture.pcapng -q -z io,phs

# 会话统计
tshark -r capture.pcapng -q -z conv,tcp

# 端点统计
tshark -r capture.pcapng -q -z endpoints,ip

# HTTP 请求统计
tshark -r capture.pcapng -q -z http,stat

# DNS 统计
tshark -r capture.pcapng -q -z dns,tree
```

## 30.6 实用案例

### 30.6.1 提取所有访问的域名

```bash
tshark -r capture.pcapng -Y "dns.qry.name" -T fields -e dns.qry.name | sort -u
```

### 30.6.2 统计 HTTP 状态码

```bash
tshark -r capture.pcapng -Y "http.response" -T fields -e http.response.code \
  | sort | uniq -c | sort -rn
```

### 30.6.3 找出重传最多的会话

```bash
tshark -r capture.pcapng -Y "tcp.analysis.retransmission" \
  -T fields -e ip.src -e ip.dst -e tcp.stream \
  | sort | uniq -c | sort -rn | head
```

### 30.6.4 实时提取 HTTP 请求 URL

```bash
tshark -i eth0 -f "tcp port 80" -l -Y "http.request" \
  -T fields -e http.host -e http.request.uri
```

`-l` 选项让输出立即刷新（行缓冲），适合实时监控。

## 30.7 与脚本集成

tshark 的输出容易与 Python、Shell 脚本集成。例如用 Python 处理 tshark 输出：

```python
import subprocess

result = subprocess.run(
    ["tshark", "-r", "capture.pcapng", "-Y", "http.response.code >= 400",
     "-T", "fields", "-e", "http.response.code", "-e", "http.request.uri"],
    capture_output=True, text=True
)
for line in result.stdout.splitlines():
    code, uri = line.split("\t")
    print(f"错误 {code}: {uri}")
```

或者使用 Python 的 `scapy`、`dpkt` 库直接解析 pcap 文件，避免依赖 tshark。

## 30.8 性能考虑

- 处理大文件时使用 `-Y` 尽早过滤，减少解析开销。
- `-T fields` 只输出需要的字段，比 `-V` 快得多。
- 实时抓包保存到文件（-w）比实时解析（默认）更高效。
- 需要长期抓包时，用 `dumpcap`（更轻量）或 `tshark -w` 而非 `tshark -i` 实时显示。

## 30.9 小结

- tshark 是命令行版 Wireshark，支持相同的抓包、过滤和解析能力。
- 常用参数：`-i`（接口）、`-r`（读文件）、`-w`（写文件）、`-f`（捕获过滤）、`-Y`（显示过滤）。
- `-T fields -e 字段` 提取结构化数据，是最强大的功能。
- `-z` 执行统计，`-q` 安静模式，`-V` 详细树，`-x` 十六进制。
- 输出易与 Shell/Python 集成，适合自动化分析。

下一章，学习网络性能分析的方法论。
