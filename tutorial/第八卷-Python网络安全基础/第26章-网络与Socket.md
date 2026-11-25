# 第 26 章 网络基础与 Socket 编程

## 本章目标

- 理解网络分层模型（TCP/IP）
- 理解 IP、端口、TCP/UDP、DNS 等核心概念
- 掌握 Python 的 socket 编程
- 写一个端口扫描器和一个简单的网络客户端
- 理解网络协议与安全的关系

> **伦理声明**：本章及后续安全章节的所有技术，仅用于**合法授权**的测试、学习和防守研究。请把练习目标限定为本机（127.0.0.1）、自己的靶场或 CTF 竞赛环境。未经授权扫描/攻击他人系统违反《网络安全法》《刑法》等法律法规。

网络是安全的"战场"。不懂网络协议，就无法理解攻击是怎么发生的，也无法写检测规则。

---

## 26.1 网络基础概念

### 26.1.1 TCP/IP 分层模型

网络通信像寄快递，分几层协作：

| 层 | 作用 | 典型协议 |
|----|------|---------|
| 应用层 | 具体应用的数据格式 | HTTP、DNS、SMTP、FTP |
| 传输层 | 端到端的连接和可靠性 | TCP、UDP |
| 网络层 | 寻址和路由 | IP、ICMP |
| 链路层 | 物理网络传输 | Ethernet、Wi-Fi |

### 26.1.2 核心概念

**IP 地址**：网络设备的位置编号，像"门牌号"。

```python
import ipaddress

ip = ipaddress.ip_address("192.168.1.1")
print(ip.is_private)   # True  是否私有地址
print(ip.version)      # 4     IPv4
```

**端口**：一台设备上不同服务的"窗口"（0-65535）。

```python
# 常见端口
COMMON_PORTS = {
    20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "Telnet",
    25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
    143: "IMAP", 443: "HTTPS", 3306: "MySQL", 3389: "RDP", 8080: "HTTP-Alt",
}
```

**TCP vs UDP**：

- **TCP**：可靠连接，先握手（三次握手），保证数据送达。HTTP、SSH 用 TCP
- **UDP**：无连接，速度快但不保证送达。DNS、视频流用 UDP

**三次握手**（理解端口扫描的基础）：

```
客户端 → 服务器：SYN（我想连接）
服务器 → 客户端：SYN-ACK（可以）
客户端 → 服务器：ACK（确认）
连接建立
```

### 26.1.3 DNS

DNS 把域名解析成 IP：

```python
import socket

ip = socket.gethostbyname("www.baidu.com")
print(ip)
```

---

## 26.2 Socket 编程

Socket 是网络编程的接口，可以理解为"网络通信的插座"。

### 26.2.1 TCP 客户端

```python
import socket

# 创建 socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # IPv4, TCP
s.settimeout(5)

try:
    # 连接服务器
    s.connect(("www.baidu.com", 80))
    
    # 发送 HTTP 请求
    request = "GET / HTTP/1.1\r\nHost: www.baidu.com\r\n\r\n"
    s.sendall(request.encode("utf-8"))
    
    # 接收响应
    response = s.recv(4096)
    print(response.decode("utf-8", errors="ignore")[:500])
finally:
    s.close()
```

### 26.2.2 简单的端口扫描器（TCP 连接扫描）

```python
import socket

def scan_port(host, port, timeout=0.5):
    """扫描单个端口，返回是否开放"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))  # 0 表示连接成功（端口开放）
        s.close()
        return result == 0
    except Exception:
        return False

def scan_ports(host, ports):
    """扫描多个端口"""
    open_ports = []
    for port in ports:
        if scan_port(host, port):
            open_ports.append(port)
    return open_ports

# 测试（用本机）
if __name__ == "__main__":
    target = "127.0.0.1"
    ports = [21, 22, 23, 80, 443, 3306, 3389, 8080]
    result = scan_ports(target, ports)
    print(f"{target} 开放端口: {result}")
```

> **伦理提示**：只扫描本机或授权目标。对他人系统扫描是违法行为。

### 26.2.3 多线程加速扫描

```python
import socket
from concurrent.futures import ThreadPoolExecutor

def scan_port(host, port):
    try:
        s = socket.socket()
        s.settimeout(0.3)
        result = s.connect_ex((host, port))
        s.close()
        return port if result == 0 else None
    except Exception:
        return None

def fast_scan(host, ports, max_workers=50):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(lambda p: scan_port(host, p), ports)
    return [p for p in results if p is not None]

# 使用
ports = range(1, 1025)   # 扫描 1-1024 端口
open_ports = fast_scan("127.0.0.1", ports)
print("开放端口:", open_ports)
```

多线程把几百个端口的扫描从几分钟缩短到几秒。这也是很多安全工具的基本原理。

### 26.2.4 简单的 TCP 服务器

```python
import socket

def simple_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 9999))
    server.listen(5)
    print("服务器启动，监听 9999 端口")
    
    while True:
        client, addr = server.accept()   # 等待客户端连接
        print(f"客户端 {addr} 连接")
        data = client.recv(1024)
        client.sendall(b"Hello from server!")
        client.close()

# simple_server()   # 取消注释运行
```

---

## 26.3 用 Scapy 做底层网络操作

Scapy 是强大的网络包构造和分析工具：

```bash
pip install scapy
```

```python
from scapy.all import ARP, Ether, srp

# ARP 扫描：发现局域网内的存活主机（仅在自己的网络）
def arp_scan(network="192.168.1.0/24"):
    arp = ARP(pdst=network)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp
    result = srp(packet, timeout=3, verbose=0)[0]
    
    clients = []
    for sent, received in result:
        clients.append({"ip": received.psrc, "mac": received.hwsrc})
    return clients

# clients = arp_scan("192.168.1.0/24")  # 仅在授权网络运行
# for c in clients: print(c)
```

> **注意**：ARP 扫描、SYN 扫描等技术是中性的，安全人员用来做资产盘点和防御测试，攻击者用来侦察。学习它们是为了理解攻击原理、更好地防御。

---

## 26.4 网络协议与安全

| 协议 | 常见安全风险 |
|------|------------|
| HTTP | 明文传输，可被嗅探、篡改（用 HTTPS） |
| DNS | DNS 劫持、DNS 隧道 |
| ARP | ARP 欺骗（中间人攻击） |
| TCP | SYN Flood（DDoS）、TCP 会话劫持 |
| FTP/Telnet | 明文密码（用 SFTP/SSH 替代） |

理解协议，才能理解攻击面，也才能设计检测规则。

---

## 26.5 本章总结

| 知识点 | 核心内容 |
|--------|---------|
| TCP/IP | 应用层/传输层/网络层/链路层 |
| IP/端口 | 地址+窗口；常见端口要记 |
| TCP vs UDP | 可靠 vs 快速；三次握手 |
| Socket | `socket.socket()`；`connect_ex` 判断端口 |
| 端口扫描 | TCP 连接扫描 + 多线程加速 |
| Scapy | 构造/分析网络包；ARP 扫描 |
| 协议安全 | 各协议的典型风险 |

---

## 本章练习

1. 写一个端口扫描器，支持指定端口范围。
2. 用多线程优化扫描器，对比速度。
3. 用 socket 写一个简单的 HTTP 客户端，获取网站响应头。
4. 思考：TCP 连接扫描和 SYN 扫描有什么区别？（提示：三次握手是否完成）
5. 用 Scapy 抓取几个网络包，观察其结构。

---

**下一章预告**：我们将学习加密基础与 Web 安全——哈希、对称/非对称加密、常见 Web 漏洞（SQL 注入、XSS）的原理和防御。
